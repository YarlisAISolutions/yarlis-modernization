#!/usr/bin/env python3
"""Draft legacy-to-target mapping (mainframe -> React + Spring Boot + DB2) from inventory.json.

Produces a first draft for SRD sections 7.2 (data mapping) and 12 (component mapping). Every suggested
name is a heuristic: review, rename to business terms, and record decisions as ADRs.

Usage:
  mapgen.py --inventory docs/analysis/inventory.json [--out docs/analysis/target-mapping.md]
            [--data-out docs/analysis/data-mapping.md] [--programs P1 P2 ...]   # limit to a slice

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

CRUD_HTTP = {"R": "GET", "C": "POST", "U": "PUT", "D": "DELETE"}
SUFFIXES = re.compile(r"(DAT|DATA|FILE|FIL|AIX|KSDS|PATH|VSAM|TBL|TAB)$")
UTILITIES = {
    "IDCAMS": "Housekeeping (VSAM define/delete/REPRO): usually dropped; REPRO loads become data-migration or a load tasklet",
    "IEFBR14": "Dataset allocation/deletion: dropped (file lifecycle handled by the job)",
    "IEBGENER": "File copy: Tasklet or dropped",
    "SORT": "Sort/merge/filter: SQL ORDER BY / GROUP BY in the reader, or a sort step. Read the control cards for hidden rules",
    "ICETOOL": "Sort/report utility: SQL aggregation or a reporting step",
    "DFSORT": "Sort: as SORT",
    "SYNCSORT": "Sort: as SORT",
    "IKJEFT01": "TSO batch (DB2 DSN RUN): the RUN PROGRAM is the real step",
    "DFSRRC00": "IMS batch region: the PSB program becomes a Spring Batch step on migrated data",
    "FTP": "File transfer: managed file transfer / object storage integration (IFR)",
    "SDSF": "Operator command (open/close CICS files): dropped or ops runbook",
    "DFHCSDUP": "CICS resource definition: dropped (infrastructure)",
}


def kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def pascal(s: str) -> str:
    return "".join(w.capitalize() for w in re.split(r"[^A-Za-z0-9]+", s) if w)


def camel(s: str) -> str:
    p = pascal(s)
    return p[:1].lower() + p[1:]


def entity_of(resource: str) -> str:
    base = resource.split(" ")[0].split(".")[-1].upper()
    base = SUFFIXES.sub("", base) or base
    return base.lower()


def screen_title(inv: dict, mapset: str | None, mapname: str | None) -> str | None:
    sc = inv["screens"].get(mapset or "")
    if not sc:
        return None
    for m in sc["maps"]:
        if mapname and m["map"] != mapname:
            continue
        for f in m["fields"]:
            pos = f.get("pos") or ""
            row = re.match(r"\(?(\d+)", pos)
            text = (f.get("initial") or "").strip()
            # a short heading near the top; skip header literals (Tran:/Date:) and long banners/instructions
            if f["role"] == "label" and row and 3 <= int(row.group(1)) <= 8 and 5 < len(text) <= 30 \
                    and not text.endswith(":") and not re.match(r"^(Tran|Date|Prog|Time|This is|Please|Press|Enter|Type)\b", text, re.I) \
                    and not re.search(r"\b(application|demo)\b", text, re.I):
                return text
    return None


def online_rows(inv, only):
    rows, used_titles = [], set()
    prog2tran = defaultdict(list)
    for t, d in inv["transactions"].items():
        prog2tran[d.get("program")].append(t)
    for pid, p in sorted(inv["programs"].items()):
        if only and pid not in only:
            continue
        if not (p.get("maps") or p.get("cics_commands")):
            continue
        maps = sorted({(m.get("mapset"), m.get("map")) for m in p.get("maps", [])}, key=str)
        title = next((screen_title(inv, ms, mp) for ms, mp in maps if screen_title(inv, ms, mp)), None)
        if title and title in used_titles:  # two screens share a heading (list + detail): keep routes unique
            title = f"{title} {maps[0][1] or pid}"
        used_titles.add(title)
        page = pascal(title) + "Page" if title else (pascal(maps[0][1] or pid) + "Page" if maps else None)
        route = "/" + kebab(title) if title else ("/" + kebab(pid))
        data = {**p.get("cics_files", {}), **{"DB2:" + k: v for k, v in p.get("sql_tables", {}).items()}}
        ents = sorted({entity_of(r.replace("DB2:", "")) for r in data})
        endpoints = []
        for r, crud in sorted(data.items()):
            e = entity_of(r.replace("DB2:", ""))
            for c in crud:
                path = f"/api/{kebab(e)}s" + ("" if c == "C" else "/{id}")
                if "R" == c and any(cmd in p.get("cics_commands", {}) for cmd in ("STARTBR", "READNEXT", "READPREV")):
                    path = f"/api/{kebab(e)}s?after={{key}}&size={{n}}"
                endpoints.append(f"{CRUD_HTTP[c]} {path}")
        kind = "screen" if maps else ("service (LINK target)" if p.get("called_by") and not maps else "online program")
        rows.append({
            "legacy": pid, "trans": ", ".join(prog2tran.get(pid, [])) or "—", "kind": kind,
            "maps": ", ".join(f"{a}/{b}" for a, b in maps) or "—", "title": title or "—",
            "react": f"`{page}` at `{route}`" if page else "—",
            "service": ", ".join(f"{kebab(e)}-service" for e in ents) or "—",
            "endpoints": "; ".join(dict.fromkeys(endpoints)) or "—",
            "nav": ", ".join(p.get("xctl", [])) or "—",
            "unit_of_work": "SYNCPOINT" if "SYNCPOINT" in p.get("cics_commands", {}) else "implicit (task end)",
        })
    return rows


def batch_rows(inv, only):
    rows = []
    for j, job in sorted(inv["jobs"].items()):
        steps = [s for s in job["steps"] if "step" in s]
        if only and not any(s.get("pgm") in only for s in steps):
            continue
        for s in steps:
            pgm = s.get("pgm") or ("PROC " + str(s.get("proc")))
            p = inv["programs"].get(s.get("pgm") or "")
            reads = [d["dd"] for d in s["dds"] if d.get("crud") == "R"]
            writes = [d["dd"] for d in s["dds"] if d.get("crud") in ("C", "U")]
            if p:
                # the program's own file usage (SELECT/ASSIGN ddnames + OPEN mode) beats the JCL DDs (libraries, concatenations)
                bf = p.get("batch_files", {})
                if bf:
                    reads = [dd for dd, c in bf.items() if c == "R"]
                    writes = [dd for dd, c in bf.items() if set(c) & set("CU")]
                tables = p.get("sql_tables", {})
                reads += [f"DB2:{t}" for t, c in tables.items() if "R" in c]
                writes += [f"DB2:{t}" for t, c in tables.items() if set(c) & set("CUD")]
                target = (f"Chunk step `{camel(j)}{pascal(s['step'] or '')}Step`: "
                          f"reader({', '.join(reads[:3]) or '?'}) → processor({pgm} logic) → writer({', '.join(writes[:3]) or '?'})")
            else:
                util = UTILITIES.get((s.get("pgm_via") or s.get("pgm") or "").upper(), "Unknown utility/program: investigate")
                target = util
            rows.append({"job": j, "step": s["step"], "pgm": pgm + (f" (via {s['pgm_via']})" if s.get("pgm_via") else ""),
                         "cond": s.get("cond") or "—", "target": target, "spring_job": f"`{camel(j)}Job`"})
    return rows


def data_rows(inv, only=None):
    rows = []
    used_files = used_tables = None
    if only is not None:
        used_files = {f for p in only for f in inv["programs"].get(p, {}).get("cics_files", {})}
        used_tables = {t for p in only for t in inv["programs"].get(p, {}).get("sql_tables", {})}
    for f, d in sorted(inv["cics_files"].items()):
        if used_files is not None and f not in used_files:
            continue
        dsn = d.get("dsn") or ""
        kind = "VSAM AIX path → secondary index" if "AIX" in dsn or "PATH" in dsn else "VSAM KSDS → DB2 table"
        rows.append({"legacy": f"CICS FILE {f}", "dsn": dsn or "—", "target": f"table `{entity_of(f).upper()}`" if "AIX" not in dsn else "index on base table", "note": kind})
    for t in sorted(inv["tables"]):
        if used_tables is not None and t not in used_tables:
            continue
        rows.append({"legacy": f"DB2 {t}", "dsn": "—", "target": f"table `{t}` (keep; review types)", "note": "existing DB2: migrate schema + data"})
    for name, d in sorted(inv.get("ims", {}).items()):
        if d.get("kind") == "ims-dbd" and only is None:
            segs = ", ".join(s["name"] for s in d.get("segments", []))
            rows.append({"legacy": f"IMS DBD {d.get('dbd') or name}", "dsn": "—", "target": f"one table per segment ({segs}); parent key as FK", "note": "hierarchical → relational"})
    return rows


def src_link(meta: dict, rel: str, from_dir: Path) -> str:
    """Link to the source file: repo permalink (from the scan's git info) or a relative path."""
    url, ref, sub = meta.get("repo_url"), meta.get("repo_ref"), (meta.get("repo_subdir") or "").strip("/")
    if url and ref:
        p = f"{sub}/{rel}" if sub else rel
        return f"[{rel}]({url}{'/-' if 'gitlab' in url else ''}/blob/{ref}/{p})"
    import os
    return f"[{rel}]({os.path.relpath(Path(meta['source_root']) / rel, from_dir.resolve())})"


def copybook_mapping(inv, only_copies, dout_dir: Path, only_tables=None):
    out = ["# Data mapping drafts (copybook → DB2 / Java)", "",
           "Mechanical first draft. Column names drop the common field prefix; types come from the PIC clause.",
           "Review every REDEFINES / OCCURS / FILLER / date field. Rules: `references/data-vsam-db2.md`.", ""]
    for name, c in sorted(inv["copybooks"].items()):
        fields = [f for f in c.get("fields", []) if "pic" in f]
        # BMS symbolic maps are screen buffers, not data: the screens report covers them
        if name in inv["screens"] or "bms" in c["path"].lower():
            continue
        if not fields or (only_copies is not None and name not in only_copies):
            continue
        names = [f["name"] for f in fields if f["name"] != "FILLER"]
        prefix = ""
        if len(names) > 1:
            first = names[0].split("-")[0] + "-"
            if all(n.startswith(first) for n in names):
                prefix = first
        out += [f"## {name}  ", f"Source: {src_link(inv['meta'], c['path'], dout_dir)}", "",
                "| Legacy field | PIC / usage | Target column | DB2 type | Java field | Java type | Note |",
                "|---|---|---|---|---|---|---|"]
        ddl = []
        for f in fields:
            if f["name"] == "FILLER":
                out.append(f"| FILLER | {f['pic']} | — | — | — | — | unused bytes: confirm and drop |")
                continue
            base = f["name"][len(prefix):] if prefix and f["name"].startswith(prefix) else f["name"]
            col = base.replace("-", "_").upper()
            notes = []
            if f.get("redefines"):
                notes.append(f"REDEFINES {f['redefines']}: variant layout, decide discriminator")
            if f.get("occurs"):
                notes.append(f"OCCURS {f['occurs']}: child table or JSON")
            if re.search(r"DATE|DT$|_DT_", col):
                notes.append("date: confirm format → DATE")
            if f.get("usage") == "COMP-3":
                notes.append("packed decimal")
            out.append(f"| {f['name']} | {f['pic']} {f.get('usage', '')} | {col} | {f.get('db2', '?')} | {camel(base)} | {f.get('java', '?')} | {'; '.join(notes)} |")
            if not f.get("redefines") and not f.get("occurs"):
                ddl.append(f"  {col:<30} {f.get('db2', 'CHAR(1)')}")
        out += ["", "```sql", f"-- draft: name the table, set NOT NULL and the PRIMARY KEY from the VSAM key / business key",
                f"CREATE TABLE {re.sub(r'[^A-Z0-9_]', '_', name)} (", ",\n".join(ddl), ");", "```", ""]
    # existing DB2 tables (DDL/DCLGEN): already relational, map columns to Java and flag keys/constraints
    for t, d in sorted(inv["tables"].items()):
        if only_tables is not None and t not in only_tables:
            continue
        out += [f"## DB2 table {t}  ", f"Source: {src_link(inv['meta'], d['path'], dout_dir)} ({d.get('source')}); keep the table, review types",
                "", "| Column | DB2 type | Null | Java field | Java type | Note |", "|---|---|---|---|---|---|"]
        for c in d["columns"]:
            ty = c["type"]
            jt = ("String" if re.match(r"(VAR)?CHAR|CLOB|GRAPHIC", ty) else "BigDecimal" if re.match(r"DEC|NUM", ty)
                  else "LocalDate" if ty == "DATE" else "LocalDateTime" if ty.startswith("TIMESTAMP") else "LocalTime" if ty == "TIME"
                  else "short" if ty == "SMALLINT" else "int" if ty == "INTEGER" else "long" if ty == "BIGINT" else "?")
            note = "PK" if c["name"] in d.get("primary_key", []) else ""
            out.append(f"| {c['name']} | {ty} | {'Y' if c['nullable'] else 'N'} | {camel(c['name'])} | {jt} | {note} |")
        for fk in d.get("foreign_keys", []):
            out.append(f"\nFK {', '.join(fk['columns'])} → {fk['references']}" + (f" ON DELETE {fk['on_delete']}" if fk.get("on_delete") else ""))
        out.append("")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inventory", default="docs/analysis/inventory.json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--data-out", default=None)
    ap.add_argument("--programs", nargs="*", help="limit to these programs (e.g. from inventory.py slice)")
    a = ap.parse_args()
    inv = json.loads(Path(a.inventory).read_text())
    base = Path(a.inventory).parent
    out = Path(a.out) if a.out else base / "target-mapping.md"
    dout = Path(a.data_out) if a.data_out else base / "data-mapping.md"
    only = set(x.upper() for x in a.programs) if a.programs else None
    only_copies = {c for p in only for c in inv["programs"].get(p, {}).get("copies", [])} if only else None

    md = ["# Legacy → target mapping (draft)", "",
          "Target: React SPA + Spring Boot services + Spring Batch + DB2. Suggested names are heuristics from screen titles",
          "and data resources: rename to business terms. Copy reviewed rows into SRD §18.1 (data: §7.2) and record choices as ADRs (§21).", "",
          "## Online (CICS) → React + REST", "",
          "| Legacy program | TRANSID | Kind | BMS map | Screen title | React page / route | Spring Boot service | REST endpoints (draft) | Navigates to | Unit of work |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in online_rows(inv, only):
        md.append(f"| {r['legacy']} | {r['trans']} | {r['kind']} | {r['maps']} | {r['title']} | {r['react']} | {r['service']} | {r['endpoints']} | {r['nav']} | {r['unit_of_work']} |")
    md += ["", "## Batch (JCL) → Spring Batch", "", "| Job | Step | Program | COND | Target (draft) | Spring Batch job |", "|---|---|---|---|---|---|"]
    for r in batch_rows(inv, only):
        md.append(f"| {r['job']} | {r['step']} | {r['pgm']} | {r['cond']} | {r['target']} | {r['spring_job']} |")
    md += ["", "## Data stores → DB2", "", "| Legacy store | Dataset | Target | Note |", "|---|---|---|---|"]
    for r in data_rows(inv, only):
        md.append(f"| {r['legacy']} | {r['dsn']} | {r['target']} | {r['note']} |")
    md += ["", f"Field-level drafts: `{dout.name}`."]
    out.write_text("\n".join(md) + "\n")
    only_tables = {t for p in only for t in inv["programs"].get(p, {}).get("sql_tables", {})} if only else None
    dout.write_text(copybook_mapping(inv, only_copies, dout.parent, only_tables))
    print(f"Wrote {out} and {dout}")


if __name__ == "__main__":
    main()
