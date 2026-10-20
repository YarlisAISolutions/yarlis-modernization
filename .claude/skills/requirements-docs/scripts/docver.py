#!/usr/bin/env python3
"""Versioning, structure validation, evidence links and traceability for requirements documents.

Document types (templates in ../assets/templates are the single source of truth for structure):
  CONTEXT  PROJECT-CONTEXT.md: project facts shared by all documents (owner, users, repo, constraints)
  BRD      Business Requirements Document
  FRD      Functional Requirements Document
  SRD      System Requirements Document
  RTM      Requirements Traceability Matrix and Implementation Status
  GAP      Executive Progress and Gap Report

Commands
  init      Create a document from its template at version 0.1.0.
  bump      Snapshot the current version to history/, raise the version, add a revision row.
            Run it BEFORE editing an existing document.
  validate  Front matter, section order, IDs, traces, diagrams, evidence links, RTM statuses, staleness.
  linkify   Turn `path:line` evidence into hyperlinks to the source (repo permalink or relative link).
  trace     BR -> FR -> SR matrix (optionally injected into each document).
  rtm       sync: create/refresh RTM rows from BRD/FRD/SRD (keeps assessments); summary: counts into GAP/RTM.
  status    Versions and staleness of all documents.
  diff      Sections changed since the previous (or a given) version.

Versioning: patch = editorial; minor = content change (default per iteration); major = baseline/approval.
Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "assets" / "templates"

DOC_TYPES = {
    "CONTEXT": {"template": "project-context.md", "defines": [], "file": "PROJECT-CONTEXT.md"},
    "BRD": {"template": "brd.md", "defines": ["BO", "BR", "RUL", "ASM", "CON", "DEP", "RSK"], "file": "BRD.md"},
    "FRD": {"template": "frd.md", "defines": ["UC", "FR", "SCR", "BAT", "RPT", "INT", "MSG"], "upstream": ["BRD"], "file": "FRD.md"},
    "SRD": {"template": "srd.md", "defines": ["SR", "NFR", "IFR", "DR", "ADR"], "upstream": ["FRD", "BRD"], "file": "SRD.md"},
    "RTM": {"template": "rtm.md", "defines": [], "upstream": ["SRD", "FRD", "BRD"], "file": "RTM.md"},
    "GAP": {"template": "gap-report.md", "defines": [], "upstream": ["RTM"], "file": "GAP-REPORT.md"},
}
REQ_DOCS = ("BRD", "FRD", "SRD")
TRACE_RULES = {  # prefix -> (must reference one of, "technical" allowed)
    "BR": (["BO"], False),
    "FR": (["BR"], False),
    "UC": (["BR", "FR"], False),
    "SR": (["FR"], False),
    "NFR": (["BR", "FR", "RUL"], True),
    "IFR": (["BR", "FR", "INT"], True),
    "DR": (["BR", "FR", "RUL"], True),
}
BASIS_REQUIRED = ("BR", "FR", "SR", "NFR")
REQUIRED_DIAGRAMS = {
    "BRD": {7: 1, 8: 1, 12: 1},
    "FRD": {2: 1, 4: 1, 6: 1, 7: 1},
    "SRD": {2: 1, 3: 2, 4: 1, 7: 1, 17: 1},
}
RTM_PREFIXES = ("BR", "RUL", "FR", "SR", "NFR", "IFR", "DR")
RTM_COLS = ["ID", "Source", "Summary", "Priority", "Related", "Code status", "Code evidence", "Verification status",
            "Verification evidence", "Runtime status", "Gap / remaining work", "Next action", "Confidence"]
CODE_STATUS = ["Implemented", "Partially implemented", "Not implemented", "Blocked", "Not applicable", "Not verifiable", "Not assessed"]
VERIF_STATUS = ["Verified", "Partially verified", "Not verified", "Not verifiable", "Not assessed"]
RUNTIME_STATUS = ["Deployed", "Partially deployed", "Not deployed", "Not verifiable", "Not assessed"]
PRIORITY_WEIGHT = {"must": 3, "should": 2, "could": 1, "won't": 0, "wont": 0}

ALL_PREFIXES = sorted({p for d in DOC_TYPES.values() for p in d["defines"]}, key=len, reverse=True)
ID_RX = re.compile(r"\b(" + "|".join(ALL_PREFIXES) + r")-(\d{2,4})\b")
MERMAID_TYPES = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram", "stateDiagram-v2",
                 "erDiagram", "journey", "gantt", "pie", "mindmap", "timeline", "C4Context", "C4Container",
                 "C4Component", "C4Deployment", "quadrantChart", "requirementDiagram", "gitGraph", "block-beta",
                 "architecture-beta", "sankey-beta", "xychart-beta", "packet-beta", "kanban")
LEGACY_CODE_LANGS = ("cobol", "cbl", "jcl", "pli", "pl1", "asm", "hlasm", "rexx", "rpg", "rpgle", "natural", "easytrieve", "bms", "cics")
FINAL_STATUSES = ("Approved", "Baselined")
# `path/to/file.ext:12` or `path:12-40`, optionally inside backticks, not already a link target
EVIDENCE_RX = re.compile(r"(?<![\[(/\w])`?((?:[\w.$#@-]+/)*[\w.$#@-]+\.[A-Za-z0-9]{1,8}):(\d+)(?:-(\d+))?`?(?![\])])")


# --------------------------------------------------------------------------- parsing

def split_front_matter(text: str):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def parse_fm(fm: str) -> dict:
    out = {}
    for line in fm.splitlines():
        m = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not m:
            continue
        k, v = m.group(1), m.group(2).strip()
        if v.startswith(("[", "{")):
            try:
                out[k] = json.loads(v)
                continue
            except json.JSONDecodeError:
                pass
        out[k] = v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'" else v
    return out


def set_fm(text: str, key: str, value) -> str:
    fm, body = split_front_matter(text)
    sval = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
    if re.search(rf"^{key}:", fm, re.M):
        fm = re.sub(rf"^{key}:.*$", lambda _: f"{key}: {sval}", fm, flags=re.M)
    else:
        fm += f"\n{key}: {sval}"
    return f"---\n{fm}\n---\n{body}"


class Doc:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.text = self.path.read_text()
        fm, self.body = split_front_matter(self.text)
        self.fm = parse_fm(fm) if fm is not None else {}
        self.type = str(self.fm.get("doc_type", "")).upper()
        self.lines = self.text.splitlines()
        # generated blocks (trace/rtm/summary injections) are blanked too: they reference IDs, they don't define them
        gen = re.sub(r"<!-- (\w+):begin -->.*?<!-- \1:end -->", lambda m: "\n" * m.group(0).count("\n"), self.text, flags=re.S)
        nocomment = re.sub(r"<!--.*?-->", lambda m: "\n" * m.group(0).count("\n"), gen, flags=re.S)
        self.clean_lines = nocomment.splitlines()

    @property
    def version(self):
        return self.fm.get("version", "0.0.0")

    def sections(self):
        heads = [(i, m) for i, l in enumerate(self.lines) if (m := re.match(r"^## (\d+)\.\s+(.+?)\s*$", l))]
        out = []
        for k, (i, m) in enumerate(heads):
            end = heads[k + 1][0] if k + 1 < len(heads) else len(self.lines)
            out.append((int(m.group(1)), m.group(2), i, end))
        return out

    def definitions(self):
        """{ID: (line_no, block_text)} for IDs this doc type defines (heading or first table cell)."""
        own = DOC_TYPES.get(self.type, {}).get("defines", [])
        defs, dups = {}, []
        lines = self.clean_lines
        for i, l in enumerate(lines):
            hm = re.match(r"^(#{3,6})\s+([A-Z]+-\d{2,4})\b", l)
            tm = re.match(r"^\|\s*([A-Z]+-\d{2,4})\s*\|", l)
            m = hm or tm
            if not m:
                continue
            ident = m.group(2) if hm else m.group(1)
            if ident.split("-")[0] not in own:
                continue
            if hm:
                level = len(hm.group(1))
                j = i + 1
                while j < len(lines) and not re.match(r"^#{1,%d}\s" % level, lines[j]):
                    j += 1
                block = "\n".join(lines[i:j])
            else:
                block = l
            if ident in defs:
                dups.append(ident)
            defs[ident] = (i + 1, block)
        return defs, dups


def find_docs(paths, types=None):
    docs = []
    for p in paths:
        p = Path(p)
        files = sorted(p.glob("*.md")) if p.is_dir() else [p]
        for f in files:
            try:
                d = Doc(f)
            except (OSError, UnicodeDecodeError):
                continue
            if d.type in DOC_TYPES and (types is None or d.type in types):
                docs.append(d)
    return docs


def template_sections(doc_type: str):
    t = (TEMPLATES / DOC_TYPES[doc_type]["template"]).read_text()
    return [(int(m.group(1)), m.group(2).strip()) for m in re.finditer(r"^## (\d+)\.\s+(.+?)\s*$", t, re.M)]


def resolve_upstream(doc: Doc, seen=None):
    seen = seen or set()
    ups = []
    for d in doc.fm.get("derived_from") or []:
        if not isinstance(d, dict) or not d.get("path"):
            continue
        p = (doc.path.parent / d["path"]).resolve()
        if p.exists() and p not in seen:
            seen.add(p)
            u = Doc(p)
            ups.append((d, u))
            ups += resolve_upstream(u, seen)
    return ups


def parse_ver(v: str):
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", str(v).strip())
    if not m:
        raise ValueError(f"bad version '{v}' (expected MAJOR.MINOR.PATCH)")
    return tuple(int(x) for x in m.groups())


def load_context(start: Path) -> dict:
    """Front matter of the nearest PROJECT-CONTEXT.md (doc dir or up to 3 parents)."""
    d = start if start.is_dir() else start.parent
    for _ in range(4):
        f = d / "PROJECT-CONTEXT.md"
        if f.exists():
            ctx = Doc(f).fm
            ctx["_dir"] = str(d)
            return ctx
        d = d.parent
    return {}


def field(block: str, name: str) -> str:
    m = re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.+)", block)
    return m.group(1).strip() if m else ""


def split_row(line: str):
    cells = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip() for c in cells[1:-1]]


# --------------------------------------------------------------------------- links

def git_info(path: Path):
    def run(*args):
        try:
            return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    top = run("rev-parse", "--show-toplevel")
    if not top:
        return {}
    url = run("remote", "get-url", "origin")
    if url.startswith("git@"):
        url = re.sub(r"^git@([^:]+):", r"https://\1/", url)
    url = re.sub(r"\.git$", "", url)
    return {"top": top, "url": url, "ref": run("rev-parse", "HEAD")}


def source_link(rel_path: str, l1: int, l2: int | None, ctx: dict, doc_dir: Path) -> str:
    """Hyperlink for a source file location: repo permalink when repo_url+repo_ref are known, else relative."""
    url, ref = ctx.get("repo_url", ""), ctx.get("repo_ref", "")
    sub = (ctx.get("repo_subdir") or "").strip("/")
    p = f"{sub}/{rel_path}" if sub else rel_path
    if url and ref:
        if "gitlab" in url:
            return f"{url}/-/blob/{ref}/{p}#L{l1}" + (f"-{l2}" if l2 else "")
        if "bitbucket" in url:
            return f"{url}/src/{ref}/{p}#lines-{l1}" + (f":{l2}" if l2 else "")
        if "dev.azure.com" in url or "visualstudio.com" in url:
            return f"{url}?path=/{p}&version=GC{ref}&line={l1}" + (f"&lineEnd={l2}" if l2 else "") + "&lineStartColumn=1&lineEndColumn=200"
        return f"{url}/blob/{ref}/{p}#L{l1}" + (f"-L{l2}" if l2 else "")
    root = ctx.get("source_root")
    if root:
        base = Path(ctx.get("_dir", ".")) / root
        target = (base / rel_path).resolve()
        return os.path.relpath(target, doc_dir.resolve()).replace(os.sep, "/") + f"#L{l1}" + (f"-L{l2}" if l2 else "")
    return ""


def linkify_text(text: str, ctx: dict, doc_dir: Path):
    count, missing = 0, set()
    out = []
    in_code = in_comment = False
    local_root = Path(ctx.get("_dir", ".")) / ctx["source_root"] if ctx.get("source_root") else None
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            in_code = not in_code
        starts_comment = "<!--" in line and "-->" not in line.split("<!--", 1)[1]
        if in_code or in_comment or line.lstrip().startswith("<!--"):
            out.append(line)
            if in_comment and "-->" in line:
                in_comment = False
            elif starts_comment:
                in_comment = True
            continue

        def rep(m):
            nonlocal count
            path, l1, l2 = m.group(1), int(m.group(2)), int(m.group(3)) if m.group(3) else None
            if local_root and local_root.is_dir() and not (local_root / path).exists():
                missing.add(path)
            href = source_link(path, l1, l2, ctx, doc_dir)
            if not href:
                return m.group(0)
            count += 1
            label = f"{path}:{l1}" + (f"-{l2}" if l2 else "")
            return f"[`{label}`]({href})"
        # leave existing links alone so linkify is idempotent: only rewrite text between them
        parts = re.split(r"(\[(?:[^\[\]]|\[[^\]]*\])*\]\([^)]*\))", line)
        out.append("".join(p if i % 2 else EVIDENCE_RX.sub(rep, p) for i, p in enumerate(parts)))
    return "".join(out), count, missing


# --------------------------------------------------------------------------- init / bump

def _root_ref(src: Path, docs_dir: Path) -> str:
    """Relative path when the source is near the docs (same project), else absolute (deep ../ chains break easily)."""
    rel = os.path.relpath(src.resolve(), docs_dir.resolve())
    return rel if rel.count("..") <= 3 else str(src.resolve())


def cmd_init(a):
    t = a.type.upper()
    out = Path(a.out) if a.out else Path(a.dir) / DOC_TYPES[t]["file"]
    if out.exists() and not a.force:
        sys.exit(f"{out} exists; use bump to iterate on it (or --force to overwrite)")
    ctx = load_context(out.parent)
    project = a.project or ctx.get("project") or "Project"
    text = (TEMPLATES / DOC_TYPES[t]["template"]).read_text()
    derived = []
    ups = a.derived_from
    if ups is None and t in ("FRD", "SRD", "RTM", "GAP"):  # default upstreams from the same folder
        ups = [str(out.parent / DOC_TYPES[u]["file"]) for u in DOC_TYPES[t].get("upstream", []) if (out.parent / DOC_TYPES[u]["file"]).exists()]
    for up in ups or []:
        u = Doc(Path(up))
        rel = os.path.relpath(u.path.resolve(), out.parent.resolve())
        derived.append({"doc_id": u.fm.get("doc_id"), "doc_type": u.type, "version": u.version, "path": rel.replace(os.sep, "/")})
    doc_id = a.id or f"{t}-{re.sub(r'[^A-Z0-9]+', '-', project.upper()).strip('-')}"
    g = git_info(Path(a.src)) if a.src else {}
    repl = {"{{DOC_ID}}": doc_id, "{{PROJECT}}": project, "{{DATE}}": date.today().isoformat(),
            "{{AUTHOR}}": a.author, "{{DERIVED_FROM}}": json.dumps(derived),
            "{{OWNER}}": a.owner or ctx.get("business_owner") or "Unknown",
            "{{SOURCE_BASELINE}}": a.source_baseline or "", "{{TARGET_STACK}}": a.target_stack or ctx.get("target_stack", ""),
            "{{REPO_URL}}": a.repo_url or g.get("url", ""), "{{REPO_REF}}": a.repo_ref or g.get("ref", ""),
            "{{SOURCE_ROOT}}": _root_ref(Path(a.src), out.parent) if a.src else "",
            "{{REPO_SUBDIR}}": os.path.relpath(Path(a.src).resolve(), Path(g["top"])) if g.get("top") and a.src else ""}
    for k, v in repl.items():
        text = text.replace(k, v)
    text = text.replace('repo_subdir: "."', 'repo_subdir: ""')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    print(f"Created {out} ({t} {doc_id} v0.1.0)" + (f", derived from {', '.join(str(d['doc_id']) + ' v' + d['version'] for d in derived)}" if derived else ""))


def cmd_bump(a):
    d = Doc(Path(a.path))
    old = d.version
    M, m, p = parse_ver(old)
    new = {"major": f"{M + 1}.0.0", "minor": f"{M}.{m + 1}.0", "patch": f"{M}.{m}.{p + 1}"}[a.level]
    hist = d.path.parent / "history"
    hist.mkdir(exist_ok=True)
    snap = hist / f"{d.path.stem}_v{old}.md"
    if snap.exists() and not a.force:
        sys.exit(f"snapshot {snap} already exists: v{old} was already bumped once. Edit the content, or pass --force.")
    shutil.copy2(d.path, snap)
    text = set_fm(d.text, "version", new)
    text = set_fm(text, "last_updated", date.today().isoformat())
    if a.status:
        text = set_fm(text, "status", a.status)
    elif a.level == "major" and d.fm.get("status") in ("Draft", "In Review"):
        text = set_fm(text, "status", "Approved")
    if a.refresh_upstream:
        derived = d.fm.get("derived_from") or []
        for item in derived:
            up = (d.path.parent / item.get("path", "")).resolve()
            if up.exists():
                item["version"] = Doc(up).version
        text = set_fm(text, "derived_from", derived)
    row = f"| {new} | {date.today().isoformat()} | {a.author} | {a.summary.replace('|', '/')} | {a.sections or 'TBD'} |"
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if re.match(r"^###\s+1\.\d+\s+Revision History", l)), None)
    if start is None:
        sys.exit("no '### 1.x Revision History' heading found")
    last = None
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("|"):
            last = i
        elif lines[i].startswith("#") or (last is not None and lines[i].strip() == ""):
            break
    if last is None:
        sys.exit("Revision History table not found")
    lines.insert(last + 1, row)
    d.path.write_text("\n".join(lines) + "\n")
    print(f"{d.path.name}: {old} -> {new} (snapshot {snap})")
    if a.sections is None:
        print("Note: 'Sections changed' is TBD; fill it in after editing (docver.py diff shows them).")


# --------------------------------------------------------------------------- validate

def section_text(doc: Doc, start: int, end: int) -> str:
    return re.sub(r"<!--.*?-->", "", "\n".join(doc.lines[start + 1:end]), flags=re.S)


def lint_mermaid(block: str):
    issues = []
    lines = [l for l in block.splitlines() if l.strip() and not l.strip().startswith("%%")]
    if not lines:
        return ["empty mermaid block"]
    head = lines[0].strip().split()[0]
    if head not in MERMAID_TYPES:
        issues.append(f"unknown diagram type '{head}'")
    if head in ("flowchart", "graph"):
        for l in lines[1:]:
            s = l.strip()
            if re.match(r"^end\b", s) or s.startswith(("subgraph", "classDef", "class ", "style ", "linkStyle", "click ")):
                continue
            for lab in re.findall(r"\[([^\]\"]*\([^\]\"]*)\]", s):
                issues.append(f"quote node labels containing '(': [{lab}] -> [\"{lab}\"]")
            if re.search(r"(^|\s|-->|---)\s*end\s*(\[|\(|-->|$)", s):
                issues.append("node id 'end' is reserved; rename it (e.g. End1)")
            if '"' not in s and (s.count("[") != s.count("]") or s.count("(") != s.count(")") or s.count("{") != s.count("}")):
                issues.append(f"unbalanced brackets: {s[:60]}")
    if head == "erDiagram":
        for l in lines[1:]:
            if re.search(r"\b[a-zA-Z_]+\s*\(\s*\d+", l) and "{" not in l and '"' not in l:
                issues.append(f"erDiagram attribute types cannot contain '(n)': {l.strip()[:60]}")
    return issues


def validate_rtm(doc: Doc, errors, warns, hard, all_docs):
    rows = rtm_rows(doc)
    if rows is None:
        errors.append("RTM table markers <!-- rtm:begin --> / <!-- rtm:end --> not found")
        return
    defined = {}
    for d in all_docs:
        if d.type in REQ_DOCS:
            for i, (ln, block) in d.definitions()[0].items():
                if i.split("-")[0] in RTM_PREFIXES:
                    defined[i] = d.type
    seen = set()
    for r in rows:
        rid = r["ID"]
        seen.add(rid)
        if defined and rid not in defined and "[RETIRED]" not in r["Summary"]:
            errors.append(f"RTM row {rid}: not defined in BRD/FRD/SRD (run docver.py rtm sync)")
        cs, vs, rs = r["Code status"], r["Verification status"], r["Runtime status"]
        if cs not in CODE_STATUS:
            errors.append(f"RTM {rid}: Code status '{cs}' not one of {', '.join(CODE_STATUS)}")
        if vs not in VERIF_STATUS:
            errors.append(f"RTM {rid}: Verification status '{vs}' not one of {', '.join(VERIF_STATUS)}")
        if rs not in RUNTIME_STATUS:
            errors.append(f"RTM {rid}: Runtime status '{rs}' not one of {', '.join(RUNTIME_STATUS)}")
        empty = lambda v: v in ("", "—", "-", "None", "N/A")
        if cs in ("Implemented", "Partially implemented") and empty(r["Code evidence"]):
            errors.append(f"RTM {rid}: '{cs}' needs Code evidence (file/symbol/endpoint link)")
        if cs in ("Implemented", "Partially implemented") and not empty(r["Code evidence"]) and "](" not in r["Code evidence"]:
            warns.append(f"RTM {rid}: Code evidence is not a link (docver.py linkify)")
        if vs in ("Verified", "Partially verified") and empty(r["Verification evidence"]):
            errors.append(f"RTM {rid}: '{vs}' needs Verification evidence (test, CI run, result)")
        if vs in ("Verified", "Partially verified") and cs in ("Not implemented", "Not assessed"):
            errors.append(f"RTM {rid}: verified but Code status is '{cs}'")
        if rs in ("Deployed", "Partially deployed") and not re.search(r"deploy|release|rollout|environment|prod|staging", r["Verification evidence"] + r["Gap / remaining work"] + r["Code evidence"], re.I):
            warns.append(f"RTM {rid}: '{rs}' without deployment evidence (cite the release/rollout)")
        if cs in ("Partially implemented", "Not implemented", "Blocked") and empty(r["Gap / remaining work"]):
            errors.append(f"RTM {rid}: '{cs}' needs Gap / remaining work")
        if cs == "Blocked" and empty(r["Next action"]):
            errors.append(f"RTM {rid}: Blocked needs the blocking decision/dependency in Next action")
        if cs != "Not assessed" and not re.match(r"^(High|Medium|Low)\b", r["Confidence"]):
            errors.append(f"RTM {rid}: Confidence must start with High | Medium | Low and give a reason")
        if cs == "Not assessed":
            (errors if hard else warns).append(f"RTM {rid}: not assessed yet")
    for rid in sorted(set(defined) - seen):
        errors.append(f"RTM: requirement {rid} ({defined[rid]}) has no row (run docver.py rtm sync)")


def validate_doc(doc: Doc, strict: bool, all_docs=None):
    errors, warns = [], []
    final = doc.fm.get("status") in FINAL_STATUSES
    hard = strict or final
    all_docs = all_docs or []

    def soft(msg):
        (errors if hard else warns).append(msg)

    for k in ("doc_type", "doc_id", "title", "version", "status", "last_updated"):
        if not doc.fm.get(k):
            errors.append(f"front matter: missing '{k}'")
    try:
        parse_ver(doc.version)
    except ValueError as e:
        errors.append(str(e))

    want = template_sections(doc.type)
    have = doc.sections()
    std = {(n, t.lower()) for n, t in want}
    have_titles = [(n, t.lower()) for n, t, _, _ in have]
    for n, t in want:
        if (n, t.lower()) not in have_titles:
            errors.append(f"missing section '## {n}. {t}'")
    order = [x for x in have_titles if x in std]
    if order != sorted(order, key=lambda x: x[0]):
        errors.append("sections are out of order")
    for n, t, s, e in have:
        if (n, t.lower()) not in std:
            warns.append(f"non-standard section '## {n}. {t}' (renumbering or renaming breaks the standard structure)")
            continue
        body = section_text(doc, s, e)
        content = [l for l in body.splitlines() if l.strip() and not l.startswith("#") and not re.match(r"^\|[-| :]+\|$", l)]
        rows = [l for l in content if l.startswith("|")]
        if not content or (rows and len(rows) == len(content) and len(rows) <= 1):
            soft(f"section {n}. {t} is empty (write content, 'Unknown' with an open question, or 'N/A: <reason>')")
        na = any(re.search(r"\bN/A\b", l) for l in content)
        req = REQUIRED_DIAGRAMS.get(doc.type, {}).get(n, 0)
        got = len(re.findall(r"^```mermaid", "\n".join(doc.lines[s:e]), re.M))
        if req and got < req and not na:
            soft(f"section {n}. {t} needs at least {req} Mermaid diagram(s), found {got}")

    for i, l in enumerate(doc.clean_lines, 1):
        if "{{" in l and "}}" in l:
            errors.append(f"L{i}: unfilled template placeholder: {l.strip()[:60]}")
        if re.search(r"\bTBD\b", l) and not l.startswith("|") and "decision" not in l.lower() \
                and not re.search(r"\b(" + "|".join(ALL_PREFIXES) + r")-\d+\s*\(TBD", l):  # "NFR-001 (TBD)" refers to a stated TBD
            soft(f"L{i}: TBD without the decision needed (write 'TBD (decision needed: ..., owner: ...)')")

    # code blocks: diagrams yes; copied legacy source no (link to it instead)
    for m in re.finditer(r"^```(\w[\w+-]*)?[^\n]*\n(.*?)^```", doc.text, re.S | re.M):
        ln = doc.text[:m.start()].count("\n") + 1
        lang = (m.group(1) or "").lower()
        if lang == "mermaid":
            for iss in lint_mermaid(m.group(2)):
                errors.append(f"L{ln}: mermaid: {iss}")
        elif lang in LEGACY_CODE_LANGS:
            warns.append(f"L{ln}: copied {lang} source; replace with a link to the source lines (docver.py linkify)")
        elif not lang and m.group(2).count("\n") > 10:
            warns.append(f"L{ln}: long unlabeled code block; if it is copied source, link to it instead")

    # evidence must be links
    if doc.type in REQ_DOCS + ("RTM",):
        unlinked = 0
        for i, l in enumerate(doc.clean_lines, 1):
            if l.startswith("```"):
                continue
            for m in EVIDENCE_RX.finditer(l):
                pre = l[:m.start()]
                if pre.endswith("[") or pre.endswith("[`") or re.search(r"\]\([^)]*$", pre):
                    continue
                unlinked += 1
        if unlinked:
            warns.append(f"{unlinked} source reference(s) like path:line are not hyperlinks (run docver.py linkify)")

    if doc.type == "RTM":
        validate_rtm(doc, errors, warns, hard, all_docs)

    defs, dups = doc.definitions()
    for dup in sorted(set(dups)):
        errors.append(f"duplicate ID {dup}")
    known = set(defs)
    ups = resolve_upstream(doc)
    for _, u in ups:
        known |= set(u.definitions()[0])
    for o in all_docs:
        if o.path != doc.path and o.type in DOC_TYPES.get(doc.type, {}).get("upstream", []) + list(REQ_DOCS):
            known |= set(o.definitions()[0])
    for ident, (ln, block) in defs.items():
        prefix = ident.split("-")[0]
        refs = {f"{p}-{n}" for p, n in ID_RX.findall(block)} - {ident}
        retired = re.search(r"\*\*Status:\*\*\s*Retired", block)
        if prefix in TRACE_RULES and not retired:
            need, tech_ok = TRACE_RULES[prefix]
            if not any(r.split("-")[0] in need for r in refs):
                if not (tech_ok and re.search(r"technical", block, re.I)):
                    errors.append(f"L{ln}: {ident} must trace to one of {'/'.join(need)}" + (" (or 'Traces to: technical (<reason>)')" if tech_ok else ""))
        if prefix in BASIS_REQUIRED and "\n" in block and not field(block, "Basis") and not retired:
            soft(f"L{ln}: {ident} has no **Basis:** (Confirmed | Derived from code (candidate) | Assumption | Proposed)")
        if prefix == "RUL":
            if not re.search(r"\*\*Source:\*\*\s*\S", block):
                errors.append(f"L{ln}: {ident} has no **Source:** (link to path:line, or the stakeholder/policy)")
            if not re.search(r"\*\*Validation status:\*\*\s*(Candidate|SME-confirmed|Rejected)", block, re.I):
                errors.append(f"L{ln}: {ident} needs **Validation status:** Candidate | SME-confirmed | Rejected")
            elif final and re.search(r"Validation status:\*\*\s*Candidate", block, re.I):
                warns.append(f"L{ln}: {ident} is still a Candidate in an {doc.fm.get('status')} document")
    for i, l in enumerate(doc.clean_lines, 1):
        if "[RETIRED]" in l:
            continue
        for p, n in ID_RX.findall(l):
            r = f"{p}-{n}"
            if r not in known:
                owner = next((t for t, d in DOC_TYPES.items() if p in d["defines"]), None)
                if owner == doc.type or ups or any(o.type == owner for o in all_docs):
                    errors.append(f"L{i}: reference to undefined {r}")

    rh = re.search(r"^###\s+1\.\d+\s+Revision History\s*\n(.*?)(?=^#)", doc.body + "\n#", re.S | re.M)
    if not rh:
        errors.append("missing '### 1.x Revision History'")
    else:
        vers = [r.split("|")[1].strip() for r in rh.group(1).splitlines() if re.match(r"^\|\s*\d+\.\d+\.\d+\s*\|", r)]
        if not vers:
            errors.append("revision history has no version rows")
        else:
            if vers[-1] != doc.version:
                errors.append(f"last revision row is {vers[-1]} but front matter version is {doc.version} (use docver.py bump)")
            try:
                pv = [parse_ver(v) for v in vers]
                if any(b <= a for a, b in zip(pv, pv[1:])):
                    errors.append("revision history versions are not strictly increasing")
            except ValueError as e:
                errors.append(str(e))
            if re.search(r"\|\s*TBD\s*\|\s*$", rh.group(1), re.M):
                warns.append("a revision row has 'Sections changed' = TBD")

    for pin, u in ups:
        if pin.get("doc_id") == u.fm.get("doc_id") and pin.get("version") != u.version:
            warns.append(f"STALE: derived from {u.fm.get('doc_id')} v{pin.get('version')} but it is now v{u.version}; "
                         f"review (docver.py diff {u.path.name} --against {pin.get('version')}) then bump with --refresh-upstream")
    return errors, warns


def cmd_validate(a):
    docs = find_docs(a.paths)
    if not docs:
        sys.exit("no requirements documents found")
    siblings = find_docs({Path(p).parent if Path(p).is_file() else Path(p) for p in a.paths})
    rc = 0
    for d in docs:
        if d.type == "CONTEXT":
            missing = [k for k in ("project", "business_owner") if not d.fm.get(k)]
            links = "permalinks" if d.fm.get("repo_url") and d.fm.get("repo_ref") else "relative links" if d.fm.get("source_root") else "NO link target"
            print(f"== {d.path} [CONTEXT] evidence links: {links}" + (f"; missing {', '.join(missing)}" if missing else ""))
            continue
        errs, warns = validate_doc(d, a.strict, siblings)
        print(f"== {d.path} [{d.type} {d.fm.get('doc_id')} v{d.version} {d.fm.get('status')}]")
        for e in errs:
            print(f"  ERROR  {e}")
        for w in warns:
            print(f"  WARN   {w}")
        if not errs and not warns:
            print("  OK")
        rc |= 1 if errs else 0
    sys.exit(rc)


# --------------------------------------------------------------------------- linkify

class _Md:
    """Any markdown file (analysis notes, rule catalogues) for linkify, with or without front matter."""

    def __init__(self, path):
        self.path, self.text = Path(path), Path(path).read_text()


def cmd_linkify(a):
    docs = []
    for p in a.paths:
        p = Path(p)
        files = sorted(p.rglob("*.md")) if p.is_dir() else [p]
        docs += [_Md(f) for f in files if "history" not in f.parts]
    for d in docs:
        ctx = load_context(d.path)
        if not ctx and a.context:
            ctx = load_context(Path(a.context))
        if a.repo_url:
            ctx["repo_url"] = a.repo_url
        if a.repo_ref:
            ctx["repo_ref"] = a.repo_ref
        if a.source_root:
            ctx["source_root"] = os.path.relpath(Path(a.source_root).resolve(), Path(ctx.get("_dir", d.path.parent)).resolve())
            ctx.setdefault("_dir", str(d.path.parent))
        if not (ctx.get("repo_url") and ctx.get("repo_ref")) and not ctx.get("source_root"):
            print(f"{d.path}: skipped, no link target (set repo_url + repo_ref or source_root in PROJECT-CONTEXT.md, "
                  "or pass --context / --repo-url --repo-ref / --source-root)")
            continue
        new, n, missing = linkify_text(d.text, ctx, d.path.parent)
        if n and not a.dry_run:
            d.path.write_text(new)
        print(f"{d.path.name}: {n} reference(s) linked" + (" (dry run)" if a.dry_run else ""))
        for m in sorted(missing):
            print(f"  WARN  {m} not found under source_root; check the path")


# --------------------------------------------------------------------------- trace

def build_trace(docs):
    by_type = {t: [d for d in docs if d.type == t] for t in DOC_TYPES}
    defs = {}
    for d in docs:
        for ident, (ln, block) in d.definitions()[0].items():
            name = re.sub(r"^#+\s+[A-Z]+-\d+\s*[:—-]?\s*", "", block.splitlines()[0]).strip("| ")
            if block.startswith("|"):
                cells = split_row(block)
                name = cells[1] if len(cells) > 1 else name
            refs = sorted({f"{p}-{n}" for p, n in ID_RX.findall(block)} - {ident})
            defs[ident] = {"doc": d, "name": name[:70], "refs": refs, "block": block}

    def children(ident, prefixes):
        return sorted(i for i, v in defs.items() if i.split("-")[0] in prefixes and ident in v["refs"])
    rows = []
    for br in sorted(i for i in defs if i.startswith("BR-")):
        frs = children(br, ["FR"])
        srs = sorted({s for f in frs for s in children(f, ["SR", "NFR", "IFR", "DR"])} | set(children(br, ["SR", "NFR", "IFR", "DR"])))
        rows.append({"BR": br, "name": defs[br]["name"], "BO": [r for r in defs[br]["refs"] if r.startswith("BO-")],
                     "RUL": sorted(set(children(br, ["RUL"]) + [r for r in defs[br]["refs"] if r.startswith("RUL-")])),
                     "UC": children(br, ["UC"]), "FR": frs, "SR": srs})
    fr_rows = [{"FR": f, "name": defs[f]["name"], "BR": [r for r in defs[f]["refs"] if r.startswith("BR-")],
                "SR": children(f, ["SR", "NFR", "IFR", "DR"])} for f in sorted(i for i in defs if i.startswith("FR-"))]
    return rows, fr_rows, by_type, defs


def render_trace(rows, fr_rows, by_type, kind="BRD"):
    out = []
    if kind in ("BRD", "ALL"):
        out += ["| BR | Requirement | Objectives | Rules | Use cases | FRs | SRD items |", "|---|---|---|---|---|---|---|"]
        for r in rows:
            out.append(f"| {r['BR']} | {r['name']} | {', '.join(r['BO']) or '—'} | {', '.join(r['RUL']) or '—'} | {', '.join(r['UC']) or '—'} | "
                       f"{', '.join(r['FR']) or ('**none**' if by_type['FRD'] else '—')} | {', '.join(r['SR']) or ('**none**' if by_type['SRD'] else '—')} |")
    if kind in ("FRD", "SRD", "ALL"):
        if out:
            out.append("")
        out += ["| FR | Requirement | Business reqs | SRD items |", "|---|---|---|---|"]
        for f in fr_rows:
            out.append(f"| {f['FR']} | {f['name']} | {', '.join(f['BR']) or '**none**'} | {', '.join(f['SR']) or ('**none**' if by_type['SRD'] else '—')} |")
    out += ["", f"Coverage: {sum(1 for r in rows if r['FR'])}/{len(rows)} BRs have FRs; "
            f"{sum(1 for f in fr_rows if f['SR'])}/{len(fr_rows)} FRs have SRD items. Generated by docver.py trace."]
    return "\n".join(out)


def inject(text: str, marker: str, block: str) -> str:
    return re.sub(rf"<!-- {marker}:begin -->.*?<!-- {marker}:end -->",
                  lambda _: f"<!-- {marker}:begin -->\n{block}\n<!-- {marker}:end -->", text, flags=re.S)


def cmd_trace(a):
    docs = find_docs([a.dir], REQ_DOCS)
    rows, fr_rows, by_type, _ = build_trace(docs)
    md = render_trace(rows, fr_rows, by_type, "ALL")
    orphans = [r["BR"] for r in rows if by_type["FRD"] and not r["FR"]] + [f["FR"] for f in fr_rows if by_type["SRD"] and not f["SR"]]
    print("# Traceability matrix\n\n" + md + ("\n\nOrphans (no downstream coverage): " + ", ".join(orphans) if orphans else ""))
    if a.inject:
        for d in docs:
            new = inject(d.text, "trace", render_trace(rows, fr_rows, by_type, d.type))
            if new != d.text:
                d.path.write_text(new)
                print(f"injected traceability into {d.path.name}")


# --------------------------------------------------------------------------- RTM

def rtm_rows(doc: Doc):
    m = re.search(r"<!-- rtm:begin -->\n(.*?)<!-- rtm:end -->", doc.text, re.S)
    if not m:
        return None
    rows = []
    for line in m.group(1).splitlines():
        if not line.startswith("|") or re.match(r"^\|[-| :]+\|$", line):
            continue
        cells = split_row(line)
        if not cells or cells[0] == "ID":
            continue
        cells += [""] * (len(RTM_COLS) - len(cells))
        rows.append(dict(zip(RTM_COLS, cells[:len(RTM_COLS)])))
    return rows


def render_rtm(rows):
    out = ["| " + " | ".join(RTM_COLS) + " |", "|" + "---|" * len(RTM_COLS)]
    for r in rows:
        out.append("| " + " | ".join((r.get(c) or "").replace("\n", " ") for c in RTM_COLS) + " |")
    return "\n".join(out)


def order_key(rid):
    p, n = rid.split("-")
    return (RTM_PREFIXES.index(p) if p in RTM_PREFIXES else 99, int(n))


def cmd_rtm(a):
    d_dir = Path(a.dir)
    rtm_path = d_dir / DOC_TYPES["RTM"]["file"]
    if not rtm_path.exists():
        sys.exit(f"{rtm_path} not found: docver.py init --type rtm --dir {d_dir}")
    rtm = Doc(rtm_path)
    if a.action == "sync":
        docs = find_docs([d_dir], REQ_DOCS)
        _, _, _, defs = build_trace(docs)
        existing = {r["ID"]: r for r in (rtm_rows(rtm) or [])}
        rows, added = [], []
        for rid in sorted((i for i in defs if i.split("-")[0] in RTM_PREFIXES), key=order_key):
            v = defs[rid]
            prio = field(v["block"], "Priority").split("|")[0].strip() or "Unknown"
            retired = bool(re.search(r"\*\*Status:\*\*\s*Retired", v["block"]))
            base = {"ID": rid, "Source": f"{v['doc'].type} v{v['doc'].version}", "Summary": v["name"].replace("|", "/"),
                    "Priority": prio if prio in ("Must", "Should", "Could", "Won't") else "Unknown",
                    "Related": ", ".join(v["refs"]) or "—"}
            if rid in existing:
                r = existing.pop(rid)
                r.update(base)
            else:
                r = dict(base, **{"Code status": "Not applicable" if retired else "Not assessed", "Code evidence": "—",
                                  "Verification status": "Not assessed", "Verification evidence": "—",
                                  "Runtime status": "Not assessed", "Gap / remaining work": "—", "Next action": "—", "Confidence": "—"})
                added.append(rid)
            if retired:
                r["Summary"] = "[RETIRED] " + r["Summary"]
            rows.append(r)
        for rid, r in existing.items():  # no longer defined anywhere: keep, flag
            if not r["Summary"].startswith("[RETIRED]"):
                r["Summary"] = "[RETIRED] " + r["Summary"]
            rows.append(r)
        text = inject(rtm.text, "rtm", render_rtm(rows))
        rtm_path.write_text(text)
        print(f"RTM synced: {len(rows)} rows, {len(added)} added" + (f" ({', '.join(added[:20])}{'…' if len(added) > 20 else ''})" if added else "")
              + (f", {len(existing)} no longer defined (flagged [RETIRED])" if existing else ""))
        return
    # summary
    rows = [r for r in (rtm_rows(rtm) or []) if not r["Summary"].startswith("[RETIRED]")]
    by_doc = defaultdict(Counter)
    for r in rows:
        by_doc[r["Source"].split()[0]][r["Code status"]] += 1
    lines = ["**Code implementation status by document**", "", "| Document | " + " | ".join(CODE_STATUS) + " | Total |", "|" + "---|" * (len(CODE_STATUS) + 2)]
    for doc_t in REQ_DOCS:
        c = by_doc.get(doc_t, Counter())
        lines.append(f"| {doc_t} | " + " | ".join(str(c[s]) for s in CODE_STATUS) + f" | {sum(c.values())} |")
    tot = Counter(r["Code status"] for r in rows)
    lines.append("| **All** | " + " | ".join(str(tot[s]) for s in CODE_STATUS) + f" | {len(rows)} |")
    vc, rc = Counter(r["Verification status"] for r in rows), Counter(r["Runtime status"] for r in rows)
    lines += ["", "**Verification status:** " + ", ".join(f"{s} {vc[s]}" for s in VERIF_STATUS),
              "", "**Runtime/deployment status:** " + ", ".join(f"{s} {rc[s]}" for s in RUNTIME_STATUS)]
    if a.weighted:
        w = {r["ID"]: PRIORITY_WEIGHT.get(r["Priority"].lower()) for r in rows}
        if any(v is None for v in w.values()):
            lines += ["", "Weighted completion not calculated: some requirements have Priority Unknown."]
        else:
            credit = {"Implemented": 1.0, "Partially implemented": 0.5}
            scope = [r for r in rows if r["Code status"] not in ("Not applicable",)]
            num = sum(w[r["ID"]] * credit.get(r["Code status"], 0) for r in scope)
            den = sum(w[r["ID"]] for r in scope) or 1
            lines += ["", f"Weighted code completion: {100 * num / den:.0f}% = Σ(weight × credit) / Σ(weight); weights Must 3, Should 2, Could 1, Won't 0; "
                      "credit Implemented 1, Partially 0.5, other 0; excludes Not applicable and retired. Code only: not verification or deployment."]
    unver = [r for r in rows if r["Code status"] in ("Implemented", "Partially implemented") and r["Verification status"] not in ("Verified",)]
    ulines = ["| ID | Summary | Code status | Verification status | Next action |", "|---|---|---|---|---|"]
    ulines += [f"| {r['ID']} | {r['Summary']} | {r['Code status']} | {r['Verification status']} | {r['Next action']} |" for r in unver] or ["| — | none | | | |"]
    summary, unverified = "\n".join(lines), "\n".join(ulines)
    rtm_path.write_text(inject(rtm.text, "summary", summary))
    gap = d_dir / DOC_TYPES["GAP"]["file"]
    if gap.exists():
        g = Doc(gap)
        gap.write_text(inject(inject(g.text, "summary", summary), "unverified", unverified))
        print(f"injected summary into {gap.name}")
    print(summary + "\n\nImplemented but not verified:\n" + unverified)


# --------------------------------------------------------------------------- status / diff

def cmd_status(a):
    docs = find_docs([a.dir])
    print("| Doc | Type | Version | Status | Updated | Derived from |\n|---|---|---|---|---|---|")
    for d in sorted(docs, key=lambda x: list(DOC_TYPES).index(x.type)):
        pins = []
        for pin, u in resolve_upstream(d):
            if pin.get("doc_id") == u.fm.get("doc_id"):
                stale = "" if pin.get("version") == u.version else f" **STALE (now v{u.version})**"
                pins.append(f"{pin.get('doc_id')} v{pin.get('version')}{stale}")
        print(f"| {d.path.name} | {d.type} | {d.version} | {d.fm.get('status')} | {d.fm.get('last_updated')} | {', '.join(pins) or '—'} |")


def cmd_diff(a):
    d = Doc(Path(a.path))
    hist = d.path.parent / "history"
    if a.against:
        snap = hist / f"{d.path.stem}_v{a.against}.md"
    else:
        snaps = sorted(hist.glob(f"{d.path.stem}_v*.md"), key=lambda p: parse_ver(p.stem.rsplit("_v", 1)[1]))
        if not snaps:
            sys.exit("no history snapshots yet")
        snap = snaps[-1]
    if not snap.exists():
        sys.exit(f"{snap} not found")
    old = Doc(snap)

    def by_section(doc):
        # generated blocks (trace/rtm/summary) don't count as an author's change
        strip = lambda s: re.sub(r"<!-- (\w+):begin -->.*?<!-- \1:end -->", "", s, flags=re.S)
        return {f"{n}. {t}": strip("\n".join(doc.lines[s:e])) for n, t, s, e in doc.sections()}
    o, n = by_section(old), by_section(d)
    changed = [k for k in n if o.get(k) != n[k]]
    print(f"{d.path.name}: v{old.version} -> v{d.version}")
    print("Sections changed: " + (", ".join(k.split(".")[0] for k in changed if k.split(".")[0] != "1") or "none"))
    for k in changed:
        print(f"  ~ {k}")
    for k in o:
        if k not in n:
            print(f"  - {k} (removed)")
    if a.full:
        sys.stdout.writelines(difflib.unified_diff(old.text.splitlines(True), d.text.splitlines(True), str(snap), str(d.path)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--type", required=True, type=str.upper, choices=list(DOC_TYPES))
    i.add_argument("--dir", default="docs/requirements", help="folder for the document (standard file name)")
    i.add_argument("--out", help="explicit output path instead of --dir/<standard name>")
    i.add_argument("--project")
    i.add_argument("--owner")
    i.add_argument("--id")
    i.add_argument("--author", default="Claude (draft)")
    i.add_argument("--derived-from", nargs="*", help="upstream doc path(s); default: the standard upstream files in the same folder")
    i.add_argument("--source-baseline")
    i.add_argument("--target-stack")
    i.add_argument("--src", help="CONTEXT: source root (git remote/commit detected for permalinks)")
    i.add_argument("--repo-url")
    i.add_argument("--repo-ref")
    i.add_argument("--force", action="store_true")
    b = sub.add_parser("bump")
    b.add_argument("path")
    b.add_argument("--level", choices=["major", "minor", "patch"], default="minor")
    b.add_argument("--summary", required=True)
    b.add_argument("--sections")
    b.add_argument("--author", default="Claude (draft)")
    b.add_argument("--status", choices=["Draft", "In Review", "Approved", "Baselined", "Superseded"])
    b.add_argument("--refresh-upstream", action="store_true")
    b.add_argument("--force", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("paths", nargs="+")
    v.add_argument("--strict", action="store_true")
    lk = sub.add_parser("linkify")
    lk.add_argument("paths", nargs="+")
    lk.add_argument("--repo-url")
    lk.add_argument("--repo-ref")
    lk.add_argument("--source-root")
    lk.add_argument("--dry-run", action="store_true")
    lk.add_argument("--context", help="PROJECT-CONTEXT.md to use for files outside the requirements folder (e.g. docs/analysis)")
    t = sub.add_parser("trace")
    t.add_argument("dir")
    t.add_argument("--inject", action="store_true")
    r = sub.add_parser("rtm")
    r.add_argument("action", choices=["sync", "summary"])
    r.add_argument("dir")
    r.add_argument("--weighted", action="store_true", help="add a priority-weighted completion figure (only if all priorities are known)")
    s = sub.add_parser("status")
    s.add_argument("dir")
    df = sub.add_parser("diff")
    df.add_argument("path")
    df.add_argument("--against")
    df.add_argument("--full", action="store_true")
    a = ap.parse_args()
    {"init": cmd_init, "bump": cmd_bump, "validate": cmd_validate, "linkify": cmd_linkify, "trace": cmd_trace,
     "rtm": cmd_rtm, "status": cmd_status, "diff": cmd_diff}[a.cmd](a)


if __name__ == "__main__":
    main()
