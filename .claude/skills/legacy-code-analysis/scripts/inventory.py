#!/usr/bin/env python3
"""Language-agnostic source inventory for legacy (and modern) codebases.

Scans a source tree, classifies every file by extension and content signature,
and extracts the cross-references needed to write requirements documents:
programs, call/transfer graph, copybooks, screens, transactions, batch jobs,
datasets, DB2 tables, and a CRUD matrix. Every extracted fact carries the
file:line it came from so later documents can cite evidence.

Deep support: COBOL (incl. CICS, embedded SQL, DL/I, MQ), JCL/PROC, BMS, CICS CSD,
DB2 DDL/DCLGEN, IMS DBD/PSB, HLASM (light). Generic support for Java, Kotlin,
C#, Python, JS/TS, PL/I, RPG, Natural, REXX, Easytrieve and SQL files: imports,
declared units, SQL table references.

Usage:
  inventory.py scan  --src <dir> [--out docs/analysis] [--exclude GLOB ...]
  inventory.py slice --inventory docs/analysis/inventory.json --root PGM|TRANSID|JOB [--depth N]

Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- classification

EXT_TYPES = {
    "cbl": "cobol", "cob": "cobol", "cobol": "cobol", "ccp": "cobol", "sqb": "cobol",
    "cpy": "copybook", "copy": "copybook", "cpb": "copybook",
    "jcl": "jcl", "job": "jcl",
    "prc": "proc", "proc": "proc",
    "bms": "bms", "csd": "csd",
    "ddl": "ddl", "dcl": "dclgen",
    "sql": "sql",
    "dbd": "ims-dbd", "psb": "ims-psb",
    "asm": "asm", "mac": "asm-macro", "mlc": "asm",
    "pli": "pli", "pl1": "pli", "inc": "pli-include",
    "rexx": "rexx", "rex": "rexx", "exec": "rexx",
    "ezt": "easytrieve", "eztp": "easytrieve",
    "rpg": "rpg", "rpgle": "rpg", "sqlrpgle": "rpg",
    "nat": "natural", "nsp": "natural", "nsn": "natural",
    "ctl": "control-cards", "ca7": "scheduler", "controlm": "scheduler",
    "java": "java", "kt": "kotlin", "scala": "scala", "groovy": "groovy",
    "cs": "csharp", "vb": "vbnet", "py": "python", "rb": "ruby", "go": "go",
    "js": "javascript", "jsx": "javascript", "ts": "typescript", "tsx": "typescript",
    "php": "php", "c": "c", "h": "c", "cpp": "cpp", "hpp": "cpp", "rs": "rust",
    "xml": "xml", "json": "json", "yaml": "yaml", "yml": "yaml", "properties": "properties",
    "md": "doc", "txt": "text", "ps": "data", "dat": "data",
}

BINARY_EXT = {"png", "jpg", "jpeg", "gif", "pdf", "zip", "jar", "class", "exe", "dll", "so", "ico", "xlsx", "docx", "pptx"}

DEFAULT_EXCLUDES = [".git", "node_modules", "target", "build", "dist", ".idea", ".vscode", "__pycache__", ".venv"]

SIGNATURES = [
    ("cobol", re.compile(r"^.{0,7}\s*(IDENTIFICATION|ID)\s+DIVISION", re.I | re.M)),
    ("jcl", re.compile(r"^//\S*\s+JOB\b", re.M)),
    ("proc", re.compile(r"^//\S*\s+PROC\b", re.M)),
    ("bms", re.compile(r"\bDFHMSD\b")),
    ("csd", re.compile(r"^\s*DEFINE\s+(PROGRAM|TRANSACTION|FILE|MAPSET)\(", re.I | re.M)),
    ("ddl", re.compile(r"^\s*CREATE\s+(TABLE|UNIQUE\s+INDEX|INDEX|VIEW|TABLESPACE)\b", re.I | re.M)),
    ("copybook", re.compile(r"^.{6}[ ]\s*(01|05|10)\s+[A-Z0-9-]+(\s+PIC|\s*\.|\s+OCCURS|\s+REDEFINES)", re.I | re.M)),
    ("ims-dbd", re.compile(r"^\s*DBD\s+NAME=", re.M)),
    ("ims-psb", re.compile(r"^\s*PCB\s+TYPE=", re.M)),
    ("asm", re.compile(r"^\S+\s+CSECT\b", re.M)),
    ("rexx", re.compile(r"^\s*/\*.*REXX", re.I)),
]

PROGRAM_TYPES = {"cobol", "asm", "pli", "rexx", "easytrieve", "rpg", "natural",
                 "java", "kotlin", "scala", "groovy", "csharp", "vbnet", "python", "ruby", "go",
                 "javascript", "typescript", "php", "c", "cpp", "rust"}


def classify(path: Path, head: str) -> str:
    ext = path.suffix.lower().lstrip(".")
    if ext in BINARY_EXT:
        return "binary"
    t = EXT_TYPES.get(ext)
    # Mainframe exports often have no extension or a generic one; sniff content.
    if t in (None, "text", "data") or ext == "":
        for name, rx in SIGNATURES:
            if rx.search(head):
                return name
        return t or "unknown"
    # A ".cbl" file that is really a copybook (no divisions) is common.
    if t == "cobol" and not SIGNATURES[0][1].search(head):
        if SIGNATURES[6][1].search(head):
            return "copybook"
    return t


# --------------------------------------------------------------------------- COBOL helpers

def cobol_lines(text: str):
    """Yield (lineno, code) for fixed-format COBOL: drop comments, sequence and id areas.

    Handles col-7 indicator ('*', '/' comment; '-' continuation; 'D' debug) and the
    cols 73-80 identification area. Falls back to free format when '>>SOURCE FREE'
    is present.
    """
    free = ">>SOURCE FREE" in text.upper() or ">>SOURCE FORMAT FREE" in text.upper()
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\n\r")
        if free:
            s = line.split("*>")[0]
            if s.strip():
                yield i, s
            continue
        if len(line) < 7:
            continue
        ind = line[6]
        if ind in "*/":
            continue
        code = line[7:72]
        if "*>" in code:
            code = code.split("*>")[0]
        if code.strip():
            yield i, (" " + code if ind == "-" else code)


class Stmt:
    """A COBOL sentence joined from several source lines; maps offsets back to line numbers."""

    def __init__(self):
        self.parts, self.starts, self.text = [], [], ""

    def add(self, ln, code):
        if self.text:
            self.text += " "
        self.starts.append((len(self.text), ln))
        self.text += code.strip()

    def line_at(self, pos: int) -> int:
        ln = self.starts[0][1]
        for off, l in self.starts:
            if off > pos:
                break
            ln = l
        return ln


def cobol_statements(text: str):
    """Join lines into sentences (split on period / END-EXEC); yield Stmt objects."""
    st = Stmt()
    for ln, code in cobol_lines(text):
        st.add(ln, code)
        if re.search(r"(END-EXEC|\.)\s*$", st.text) or len(st.starts) > 200:
            yield st
            st = Stmt()
    if st.starts:
        yield st


def mask_literals(s: str) -> str:
    """Blank out quoted literals (same length) so keywords inside strings don't match."""
    return re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: m.group(0)[0] + " " * (len(m.group(0)) - 2) + m.group(0)[-1], s)


RX = {
    "program_id": re.compile(r"PROGRAM-ID\.?\s+['\"]?([A-Z0-9#@$-]+)", re.I),
    "copy": re.compile(r"(?<![A-Z0-9-])COPY\s+['\"]?([A-Z0-9#@$-]+)", re.I),
    "sql_include": re.compile(r"EXEC\s+SQL\s+INCLUDE\s+([A-Z0-9#@$-]+)", re.I),
    "call_lit": re.compile(r"(?<![A-Z0-9-])CALL\s+['\"]([A-Z0-9#@$-]+)['\"]", re.I),
    "call_var": re.compile(r"(?<![A-Z0-9-])CALL\s+([A-Z][A-Z0-9-]*)\b(?!['\"])", re.I),
    "cics": re.compile(r"EXEC\s+CICS\s+(.*?)END-EXEC", re.I | re.S),
    "sql": re.compile(r"EXEC\s+SQL\s+(.*?)END-EXEC", re.I | re.S),
    "value_lit": re.compile(r"^\s*\d+\s+([A-Z0-9-]+)\s+.*?VALUE\s+['\"]([A-Z0-9#@$]{1,8})\s*['\"]", re.I),
    "select_assign": re.compile(r"SELECT\s+([A-Z0-9-]+)\s+ASSIGN\s+TO\s+['\"]?([A-Z0-9-]+)", re.I),
    "fd": re.compile(r"^\s*FD\s+([A-Z0-9-]+)", re.I),
    "open": re.compile(r"\bOPEN\s+(INPUT|OUTPUT|I-O|EXTEND)\s+((?:[A-Z0-9-]+\s*)+)", re.I),
    "file_io": re.compile(r"\b(READ|WRITE|REWRITE|DELETE|START)\s+([A-Z0-9-]+)", re.I),
    "paragraph": re.compile(r"^ {0,4}([A-Z0-9][A-Z0-9-]*)(\s+SECTION)?\s*\.\s*$", re.I),
    "perform": re.compile(r"\bPERFORM\s+([A-Z0-9][A-Z0-9-]*)", re.I),
    "msg_literal": re.compile(r"MOVE\s+['\"]([^'\"]{8,})['\"]\s+TO\s+([A-Z0-9-]+)", re.I),
    "cond88": re.compile(r"^\s*88\s+([A-Z0-9-]+)\s+VALUES?\s+(.+?)\.?\s*$", re.I),
    "decision": re.compile(r"\b(IF|EVALUATE|WHEN)\b", re.I),
    "compute": re.compile(r"\b(COMPUTE|ADD|SUBTRACT|MULTIPLY|DIVIDE)\b", re.I),
    "dli": re.compile(r"CALL\s+['\"](CBLTDLI|AIBTDLI)['\"]\s+USING\s+([A-Z0-9-]+)", re.I),
    "mq": re.compile(r"CALL\s+['\"](MQ[A-Z]+)['\"]", re.I),
}

CICS_KW = re.compile(r"([A-Z]+)(?:\s*\(\s*('?[^)]*'?)\s*\))?", re.I)
FILE_CRUD = {"READ": "R", "READNEXT": "R", "READPREV": "R", "STARTBR": "R", "WRITE": "C", "REWRITE": "U", "DELETE": "D"}
SQL_CRUD = [
    ("C", re.compile(r"^\s*INSERT\s+INTO\s+([A-Z0-9_.\"]+)", re.I)),
    ("U", re.compile(r"^\s*UPDATE\s+([A-Z0-9_.\"]+)", re.I)),
    ("D", re.compile(r"^\s*DELETE\s+FROM\s+([A-Z0-9_.\"]+)", re.I)),
    ("R", re.compile(r"\bFROM\s+([A-Z0-9_.\"]+(?:\s*,\s*[A-Z0-9_.\"]+)*)", re.I)),
    ("R", re.compile(r"\bJOIN\s+([A-Z0-9_.\"]+)", re.I)),
]
SQL_NOT_TABLES = {"SYSIBM.SYSDUMMY1", "DUAL", "SQLCA", "TABLE", "FINAL"}


def parse_cics(cmd: str) -> dict:
    cmd = " ".join(cmd.split())
    toks = CICS_KW.findall(cmd)
    if not toks:
        return {}
    verb = toks[0][0].upper()
    opts = {}
    for k, v in toks[1:]:
        opts[k.upper()] = v.strip()
    # two-word verbs
    if verb in ("SEND", "RECEIVE") and "MAP" in opts:
        verb = verb + " MAP"
    return {"verb": verb, "opts": opts}


def lit(v: str):
    """Return literal name if quoted, else None (variable)."""
    v = (v or "").strip()
    m = re.match(r"^['\"]([^'\"]+)['\"]$", v)
    return m.group(1).strip().upper() if m else None


def sql_tables(sql: str):
    out = []
    s = " ".join(sql.split())
    if re.match(r"^\s*(INCLUDE|WHENEVER|COMMIT|ROLLBACK|CONNECT|SET|OPEN|CLOSE|FETCH|PREPARE|EXECUTE|BEGIN|END)\b", s, re.I):
        return out
    # DECLARE CURSOR ... FOR SELECT -> reads
    for crud, rx in SQL_CRUD:
        for m in rx.finditer(s):
            for t in re.split(r"\s*,\s*", m.group(1)):
                t = t.strip().strip('"').split()[0].upper() if t.strip() else ""
                if t and not t.startswith(":") and t not in SQL_NOT_TABLES and not t.startswith("("):
                    out.append((crud, t))
        if crud in ("C", "U", "D") and out:
            # don't also count the target table of INSERT/UPDATE/DELETE as a read via FROM
            break
    return out


def analyze_cobol(path: Path, text: str, is_copybook: bool = False) -> dict:
    info = {
        "program_id": None, "copies": [], "calls": [], "dynamic_calls": [], "xctl": [], "link": [],
        "maps": [], "transids": [], "cics_files": defaultdict(set), "batch_files": defaultdict(set),
        "sql_tables": defaultdict(set), "dli": [], "mq": [], "paragraphs": [], "performs": defaultdict(set),
        "messages": [], "conditions88": [], "decisions": 0, "computations": 0, "loc": 0, "evidence": defaultdict(list),
        "commarea": [], "cics_commands": defaultdict(int), "dynamic_resolved": [],
    }
    lines = list(cobol_lines(text))
    info["loc"] = len(lines)
    values = {}
    select_map = {}  # file-name -> ddname
    current_para = None
    in_procedure = False

    for ln, code in lines:
        u = code.upper()
        if re.search(r"PROCEDURE\s+DIVISION", u):
            in_procedure = True
            current_para = "(MAIN)"
            continue
        m = RX["program_id"].search(code)
        if m and not info["program_id"]:
            info["program_id"] = m.group(1).upper()
        m = RX["value_lit"].match(code)
        if m:
            values[m.group(1).upper()] = m.group(2).upper()
        m = RX["cond88"].match(code)
        if m:
            info["conditions88"].append({"name": m.group(1).upper(), "values": m.group(2).strip(), "line": ln})
        for m in RX["copy"].finditer(code):
            name = m.group(1).upper()
            if name not in ("REPLACING",):
                info["copies"].append(name)
                info["evidence"]["copy:" + name].append(ln)
        m = RX["select_assign"].search(code)
        if m:
            select_map[m.group(1).upper()] = m.group(2).upper()
        if in_procedure:
            pm = RX["paragraph"].match(code)
            if pm and not re.match(r"^\s*(EXIT|GOBACK|STOP|END-[A-Z]+)\b", u):
                current_para = pm.group(1).upper()
                info["paragraphs"].append({"name": current_para, "line": ln})
            for m in RX["perform"].finditer(code):
                tgt = m.group(1).upper()
                if tgt not in ("UNTIL", "VARYING", "WITH", "TEST", "TIMES") and not tgt.isdigit():
                    info["performs"][current_para].add(tgt)
            info["decisions"] += len(RX["decision"].findall(code))
            info["computations"] += len(RX["compute"].findall(code))
            m = RX["open"].search(code)
            if m:
                mode = {"INPUT": "R", "OUTPUT": "C", "I-O": "U", "EXTEND": "C"}[m.group(1).upper()]
                for f in m.group(2).split():
                    f = f.upper()
                    if f in ("INPUT", "OUTPUT", "I-O", "EXTEND"):
                        break
                    dd = select_map.get(f, f)
                    info["batch_files"][dd].add(mode)
                    info["evidence"]["file:" + dd].append(ln)

    # statement-level constructs (multi-line EXEC blocks, CALL, VALUE clauses, MOVE literal TO var)
    stmts = list(cobol_statements(text))
    moves = defaultdict(set)  # variable -> literal program/file names moved into it
    for st in stmts:
        s = st.text
        m = re.match(r"^\s*\d+\s+([A-Z0-9-]+)\b.*?\bVALUE\s+(?:IS\s+)?['\"]([A-Z0-9#@$]{1,8})\s*['\"]", s, re.I)
        if m:
            values[m.group(1).upper()] = m.group(2).upper()
        for m in re.finditer(r"\bMOVE\s+['\"]([A-Z0-9#@$]{1,8})\s*['\"]\s+TO\s+([A-Z0-9-]+)", s, re.I):
            moves[m.group(2).upper()].add(m.group(1).upper())
        for m in re.finditer(r"\bMOVE\s+([A-Z][A-Z0-9-]*)\s+TO\s+([A-Z0-9-]+)", mask_literals(s), re.I):
            if m.group(1).upper() in values:
                moves[m.group(2).upper()].add(values[m.group(1).upper()])

    def resolve_var(var: str):
        v = var.upper().strip()
        if "(" in v:  # subscripted: table-driven dispatch, needs manual resolution
            return set()
        out = set(moves.get(v, set()))
        if v in values:
            out.add(values[v])
        return out

    def first(v):
        """Literal value, else the single resolved candidate, else the variable name."""
        if v is None:
            return None
        n = lit(v)
        if n:
            return n
        c = resolve_var(v)
        return sorted(c)[0] if len(c) == 1 else v.upper()

    def para_at(ln):
        cur = "(MAIN)"
        for p in info["paragraphs"]:
            if p["line"] > ln:
                break
            cur = p["name"]
        return cur

    for st in stmts:
        stmt = st.text
        masked = mask_literals(stmt)
        for m in RX["msg_literal"].finditer(stmt):
            if " " in m.group(1).strip():
                ln = st.line_at(m.start())
                info["messages"].append({"text": m.group(1).strip(), "target": m.group(2).upper(), "line": ln, "paragraph": para_at(ln)})
        for m in RX["dli"].finditer(stmt):
            info["dli"].append({"function_field": m.group(2).upper(), "line": st.line_at(m.start())})
        for m in RX["mq"].finditer(stmt):
            info["mq"].append({"api": m.group(1).upper(), "line": st.line_at(m.start())})
        for m in RX["call_lit"].finditer(stmt):
            name = m.group(1).upper()
            if name in ("CBLTDLI", "AIBTDLI") or name.startswith("MQ"):
                continue
            info["calls"].append(name)
            info["evidence"]["call:" + name].append(st.line_at(m.start()))
        for m in RX["call_var"].finditer(masked):
            var = m.group(1).upper()
            if var in ("USING",):
                continue
            ln = st.line_at(m.start())
            cands = resolve_var(var)
            if cands:
                for c in cands:
                    info["calls"].append(c)
                    info["evidence"]["call:" + c].append(ln)
            else:
                info["dynamic_calls"].append({"variable": var, "line": ln, "via": "CALL"})
        for m in RX["sql"].finditer(stmt):
            body, ln = m.group(1), st.line_at(m.start())
            inc = re.match(r"\s*INCLUDE\s+([A-Z0-9#@$-]+)", body, re.I)
            if inc:
                n = inc.group(1).upper()
                if n not in ("SQLCA", "SQLDA"):
                    info["copies"].append(n)
                    info["evidence"]["copy:" + n].append(ln)
                continue
            for crud, t in sql_tables(body):
                info["sql_tables"][t].add(crud)
                info["evidence"]["table:" + t].append(ln)
        for m in RX["cics"].finditer(stmt):
            ln = st.line_at(m.start())
            c = parse_cics(m.group(1))
            if not c:
                continue
            verb, o = c["verb"], c["opts"]
            info["cics_commands"][verb] += 1
            prog = o.get("PROGRAM")
            if verb in ("XCTL", "LINK") and prog is not None:
                key = "xctl" if verb == "XCTL" else "link"
                name = lit(prog)
                cands = {name} if name else resolve_var(prog)
                if cands:
                    for n in cands:
                        info[key].append(n)
                        info["evidence"][key + ":" + n].append(ln)
                    if not name:
                        info["dynamic_resolved"].append({"variable": prog.upper(), "via": verb, "line": ln, "candidates": sorted(cands)})
                else:
                    info["dynamic_calls"].append({"variable": prog, "line": ln, "via": verb})
            if verb in ("SEND MAP", "RECEIVE MAP"):
                mp = first(o.get("MAP"))
                ms = first(o.get("MAPSET"))
                info["maps"].append({"map": mp, "mapset": ms, "direction": verb.split()[0], "line": ln})
            if verb in ("RETURN", "START") and "TRANSID" in o:
                t = first(o["TRANSID"])
                info["transids"].append(t)
            if "COMMAREA" in o and verb in ("XCTL", "LINK", "RETURN"):
                info["commarea"].append(o["COMMAREA"].upper())
            fname = o.get("FILE") or o.get("DATASET")
            if fname is not None and verb in FILE_CRUD:
                f = first(fname)
                info["cics_files"][f].add(FILE_CRUD[verb])
                info["evidence"]["file:" + f].append(ln)

    info["literals"] = sorted(set(values.values()))
    # finalize
    for k in ("copies", "calls", "xctl", "link", "transids", "commarea"):
        info[k] = sorted(set(info[k]))
    for k in ("cics_files", "batch_files", "sql_tables"):
        info[k] = {n: "".join(sorted(v, key="CRUD".index)) for n, v in info[k].items()}
    info["performs"] = {k: sorted(v) for k, v in info["performs"].items()}
    info["evidence"] = {k: sorted(set(v))[:10] for k, v in info["evidence"].items()}
    info["cics_commands"] = dict(info["cics_commands"])
    if not info["program_id"] and not is_copybook:
        info["program_id"] = path.stem.upper()
    return info


# --------------------------------------------------------------------------- copybook layouts

PIC_RX = re.compile(r"^\s*(\d{1,2})\s+([A-Z0-9-]+|FILLER)(.*?)\.?\s*$", re.I)


def pic_to_types(pic: str, usage: str) -> dict:
    p = pic.upper().replace(" ", "")
    # expand X(5) -> count
    def count(sym):
        n = 0
        for m in re.finditer(re.escape(sym) + r"(\((\d+)\))?", p):
            n += int(m.group(2)) if m.group(2) else 1
        return n
    signed = p.startswith("S")
    if "V" in p:
        ip, dp = p.split("V", 1)
        digits_int = sum(int(m.group(2)) if m.group(2) else 1 for m in re.finditer(r"9(\((\d+)\))?", ip))
        digits_dec = sum(int(m.group(2)) if m.group(2) else 1 for m in re.finditer(r"9(\((\d+)\))?", dp))
    else:
        digits_int, digits_dec = count("9"), 0
    alnum = count("X") + count("A")
    usage = (usage or "").upper()
    if alnum and not digits_int:
        return {"kind": "alphanumeric", "length": alnum, "db2": f"CHAR({alnum})" if alnum <= 10 else f"VARCHAR({alnum})", "java": "String"}
    if digits_int or digits_dec:
        prec = digits_int + digits_dec
        if digits_dec:
            return {"kind": "decimal", "precision": prec, "scale": digits_dec, "signed": signed, "usage": usage or "DISPLAY",
                    "db2": f"DECIMAL({prec},{digits_dec})", "java": "BigDecimal"}
        if usage in ("COMP", "COMP-4", "COMP-5", "BINARY"):
            db2 = "SMALLINT" if prec <= 4 else "INTEGER" if prec <= 9 else "BIGINT"
            java = "short" if prec <= 4 else "int" if prec <= 9 else "long"
        else:
            db2 = f"DECIMAL({prec},0)" if (usage == "COMP-3" or signed or prec > 18) else ("INTEGER" if prec <= 9 else "BIGINT")
            java = "BigDecimal" if usage == "COMP-3" and prec > 18 else ("int" if prec <= 9 else "long")
        return {"kind": "numeric", "precision": prec, "signed": signed, "usage": usage or "DISPLAY", "db2": db2, "java": java}
    return {"kind": "other"}


def analyze_copybook(text: str) -> dict:
    fields, conds = [], []
    for ln, code in cobol_lines(text):
        stmt = code.strip()
        m = PIC_RX.match(stmt)
        if not m:
            continue
        level, name, rest = int(m.group(1)), m.group(2).upper(), m.group(3)
        if level == 88:
            v = re.search(r"VALUES?\s+(?:ARE\s+|IS\s+)?(.+)", rest, re.I)
            conds.append({"name": name, "values": v.group(1).strip() if v else rest.strip(), "line": ln})
            continue
        pic = re.search(r"PIC(?:TURE)?\s+(?:IS\s+)?(\S+)", rest, re.I)
        usage = re.search(r"\b(COMP-\d|COMP|BINARY|PACKED-DECIMAL|DISPLAY)\b", rest, re.I)
        occ = re.search(r"OCCURS\s+(\d+)(?:\s+TO\s+(\d+))?", rest, re.I)
        red = re.search(r"REDEFINES\s+([A-Z0-9-]+)", rest, re.I)
        f = {"level": level, "name": name, "line": ln}
        if pic:
            u = usage.group(1).upper() if usage else ""
            if u == "PACKED-DECIMAL":
                u = "COMP-3"
            f["pic"] = pic.group(1).rstrip(".")
            f.update(pic_to_types(f["pic"], u))
        if occ:
            f["occurs"] = int(occ.group(2) or occ.group(1))
        if red:
            f["redefines"] = red.group(1).upper()
        fields.append(f)
    code = " ".join(c for _, c in cobol_lines(text))
    literals = sorted(set(m.upper() for m in re.findall(r"VALUE\s+(?:IS\s+)?'([A-Z0-9#@$]{1,8})\s*'", code, re.I)))
    return {"fields": fields, "conditions88": conds, "literals": literals}


# --------------------------------------------------------------------------- JCL / PROC

def jcl_statements(text: str):
    """Yield (lineno, label, op, operands) for JCL with continuation handling."""
    cur = None
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw[:72].rstrip()
        if not line.startswith("//") or line.startswith("//*"):
            if cur:
                yield cur
                cur = None
            continue
        body = line[2:]
        if cur and body[:1] == " " and (cur[3].rstrip().endswith(",") ):
            cur = (cur[0], cur[1], cur[2], cur[3].rstrip() + body.strip().split("  ")[0])
            continue
        if cur:
            yield cur
        m = re.match(r"^(\S*)\s+(\S+)\s*(.*)$", body)
        if not m:
            cur = None
            continue
        operands = m.group(3)
        # strip trailing comments: operands end at first blank outside quotes
        out, q = [], False
        for ch in operands:
            if ch == "'":
                q = not q
            if ch == " " and not q:
                break
            out.append(ch)
        cur = (i, m.group(1).upper(), m.group(2).upper(), "".join(out))
    if cur:
        yield cur


def kv(operands: str) -> dict:
    res, depth, key, buf, q = {}, 0, None, [], False
    parts, cur = [], []
    for ch in operands:
        if ch == "'":
            q = not q
        if not q:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append("".join(cur))
                cur = []
                continue
        cur.append(ch)
    parts.append("".join(cur))
    for i, p in enumerate(parts):
        if "=" in p:
            k, v = p.split("=", 1)
            res[k.upper()] = v
        elif i == 0 and p:
            res["_POSITIONAL"] = p
    return res


SYSTEM_DDS = {"STEPLIB", "JOBLIB", "SYSPRINT", "SYSOUT", "SYSUDUMP", "SYSABEND", "SYSMDUMP", "CEEDUMP",
              "SYSTSPRT", "SYSDBOUT", "SYSIN", "SYSTSIN", "DFSRESLB", "IMS", "SYSLIB", "SORTLIB"}


def disp_crud(disp: str) -> str:
    d = (disp or "").strip("()").upper().split(",")[0] or "NEW"
    return {"NEW": "C", "SHR": "R", "OLD": "U", "MOD": "U"}.get(d, "R")


def analyze_jcl(text: str) -> dict:
    job, steps, procs_defined, cur = None, [], [], None
    for ln, label, op, operands in jcl_statements(text):
        if op == "JOB":
            job = label
        elif op == "PROC":
            procs_defined.append(label)
        elif op == "EXEC":
            p = kv(operands)
            pgm = p.get("PGM")
            proc = p.get("PROC") or (p.get("_POSITIONAL") if not pgm else None)
            cur = {"step": label, "line": ln, "pgm": pgm.upper() if pgm else None,
                   "proc": proc.upper() if proc else None, "cond": p.get("COND"), "parm": p.get("PARM"), "dds": []}
            steps.append(cur)
        elif op == "DD" and cur is not None:
            p = kv(operands)
            dsn = p.get("DSN") or p.get("DSNAME")
            # unlabeled DD = concatenation to the previous ddname
            name = label or (cur["dds"][-1]["dd"] if cur["dds"] else "(concat)")
            if name in SYSTEM_DDS:
                continue
            dd = {"dd": name, "line": ln}
            if dsn:
                dd["dsn"] = dsn.upper()
                dd["disp"] = p.get("DISP", "")
                dd["crud"] = disp_crud(p.get("DISP", ""))
            elif "SYSOUT" in p:
                dd["sysout"] = p["SYSOUT"]
            elif p.get("_POSITIONAL") in ("*", "DATA"):
                dd["instream"] = True
            cur["dds"].append(dd)
        elif op in ("IF", "THEN", "ELSE", "ENDIF"):
            steps.append({"control": op, "line": ln, "expr": operands})
    # DB2 batch: IKJEFT01 + SYSTSIN "DSN SYSTEM(..) / RUN PROGRAM(X)" runs the real program
    for i, raw in enumerate(text.splitlines(), 1):
        m = re.search(r"\bRUN\s+PROG(?:RAM)?\s*\(\s*([A-Z0-9#@$]+)\s*\)", raw, re.I)
        if m and not raw.startswith("//*"):
            owner = [s for s in steps if "step" in s and s["line"] < i]
            if owner and not owner[-1].get("run_program"):
                owner[-1]["run_program"] = m.group(1).upper()
                owner[-1]["pgm_via"] = owner[-1]["pgm"]
                owner[-1]["pgm"] = m.group(1).upper()
    return {"job": job, "procs_defined": procs_defined, "steps": steps}


# --------------------------------------------------------------------------- BMS / CSD / DDL / IMS

def asm_statements(text: str):
    """Assembler-style continuation (non-blank col 72) used by BMS and macros."""
    cur, start = "", None
    for i, raw in enumerate(text.splitlines(), 1):
        if raw.startswith("*") or not raw.strip():
            continue
        body = raw[:71].rstrip()
        cont = len(raw) > 71 and raw[71] not in (" ", "\t")
        if cur:
            cur += body.strip()
        else:
            cur, start = body, i
        if not cont:
            yield start, cur
            cur = ""
    if cur:
        yield start, cur


def analyze_bms(text: str) -> dict:
    mapset, maps, cur = None, [], None
    for ln, stmt in asm_statements(text):
        m = re.match(r"^(\S*)\s+(DFHMSD|DFHMDI|DFHMDF)\s*(.*)$", stmt)
        if not m:
            continue
        label, macro, ops = m.group(1).upper(), m.group(2), m.group(3)
        p = kv(ops)
        if macro == "DFHMSD" and label and p.get("TYPE", "").upper() != "FINAL":
            mapset = label
        elif macro == "DFHMDI":
            cur = {"map": label, "line": ln, "size": p.get("SIZE"), "fields": []}
            maps.append(cur)
        elif macro == "DFHMDF" and cur is not None:
            attrb = p.get("ATTRB", "").strip("()").upper()
            fld = {"name": label or None, "line": ln, "pos": p.get("POS"), "length": int(p["LENGTH"]) if p.get("LENGTH", "").isdigit() else None,
                   "attrb": attrb, "initial": (p.get("INITIAL") or "").strip("'") or None}
            fld["role"] = ("input" if "UNPROT" in attrb or ("PROT" not in attrb and "ASKIP" not in attrb and label) else
                           "output" if label else "label")
            if "NUM" in attrb.split(","):
                fld["numeric"] = True
            if "DRK" in attrb.split(","):
                fld["hidden"] = True
            cur["fields"].append(fld)
    return {"mapset": mapset, "maps": maps}


def analyze_csd(text: str) -> dict:
    out = {"programs": [], "transactions": {}, "files": {}, "mapsets": []}
    for m in re.finditer(r"DEFINE\s+(PROGRAM|TRANSACTION|FILE|MAPSET)\(\s*([A-Z0-9#@$]+)\s*\)(.*?)(?=DEFINE\s|\Z)", text, re.I | re.S):
        kind, name, rest = m.group(1).upper(), m.group(2).upper(), m.group(3)
        if kind == "PROGRAM":
            out["programs"].append(name)
        elif kind == "TRANSACTION":
            p = re.search(r"PROGRAM\(\s*([A-Z0-9#@$]+)", rest, re.I)
            out["transactions"][name] = p.group(1).upper() if p else None
        elif kind == "FILE":
            d = re.search(r"DSNAME\(\s*([A-Z0-9.#@$]+)", rest, re.I)
            out["files"][name] = d.group(1).upper() if d else None
        else:
            out["mapsets"].append(name)
    return out


def analyze_ddl(text: str) -> dict:
    tables, indexes = {}, []
    clean = re.sub(r"--[^\n]*", "", text)
    for m in re.finditer(r"CREATE\s+TABLE\s+([A-Z0-9_.\"]+)\s*\((.*?)\)\s*(?:IN\s+[^;]*)?;", clean, re.I | re.S):
        name = m.group(1).strip('"').upper()
        body = m.group(2)
        cols, pk, fks = [], [], []
        depth, cur, parts = 0, [], []
        for ch in body:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(cur)); cur = []
            else:
                cur.append(ch)
        parts.append("".join(cur))
        for p in parts:
            p = " ".join(p.split())
            if not p:
                continue
            pm = re.match(r"(?:CONSTRAINT\s+\S+\s+)?PRIMARY\s+KEY\s*\(([^)]*)\)", p, re.I)
            # DB2 allows a constraint name after FOREIGN KEY: FOREIGN KEY name (cols) REFERENCES t (cols) ON DELETE x
            fm = re.match(r"(?:CONSTRAINT\s+\S+\s+)?FOREIGN\s+KEY\s*(?:[A-Z0-9_\"]+\s*)?\(([^)]*)\)\s*REFERENCES\s+([A-Z0-9_.\"]+)\s*(?:\(([^)]*)\))?(.*)$", p, re.I)
            if pm:
                pk = [c.strip().upper() for c in pm.group(1).split(",")]
            elif fm:
                od = re.search(r"ON\s+DELETE\s+(RESTRICT|CASCADE|SET\s+NULL|NO\s+ACTION)", fm.group(4) or "", re.I)
                fks.append({"columns": [c.strip().upper() for c in fm.group(1).split(",")], "references": fm.group(2).strip('"').upper(),
                            "ref_columns": [c.strip().upper() for c in (fm.group(3) or "").split(",") if c.strip()],
                            "on_delete": od.group(1).upper() if od else None})
            else:
                cm = re.match(r"([A-Z0-9_\"]+)\s+([A-Z]+(?:\s*\([^)]*\))?)(.*)$", p, re.I)
                if cm:
                    cols.append({"name": cm.group(1).strip('"').upper(), "type": cm.group(2).upper().replace(" ", ""),
                                 "nullable": "NOT NULL" not in cm.group(3).upper()})
        tables[name] = {"columns": cols, "primary_key": pk, "foreign_keys": fks}
    for m in re.finditer(r"CREATE\s+(UNIQUE\s+)?INDEX\s+([A-Z0-9_.\"]+)\s+ON\s+([A-Z0-9_.\"]+)\s*\(([^)]*)\)", clean, re.I | re.S):
        indexes.append({"name": m.group(2).upper(), "table": m.group(3).upper(), "unique": bool(m.group(1)),
                        "columns": " ".join(m.group(4).split())})
    return {"tables": tables, "indexes": indexes}


def analyze_ims(text: str, kind: str) -> dict:
    if kind == "ims-dbd":
        n = re.search(r"DBD\s+NAME=([A-Z0-9#@$]+)", text)
        segs = re.findall(r"SEGM\s+NAME=([A-Z0-9#@$]+)(?:,PARENT=([A-Z0-9#@$]+))?", text)
        return {"dbd": n.group(1) if n else None, "segments": [{"name": s, "parent": p or None} for s, p in segs]}
    pcbs = re.findall(r"PCB\s+TYPE=(DB|TP)(?:,DBDNAME=([A-Z0-9#@$]+))?", text)
    n = re.search(r"PSBGEN\s+.*?PSBNAME=([A-Z0-9#@$]+)", text, re.S)
    return {"psb": n.group(1) if n else None, "pcbs": [{"type": t, "dbd": d or None} for t, d in pcbs]}


# --------------------------------------------------------------------------- generic languages

GENERIC = {
    "imports": re.compile(r"^\s*(?:import|from|using|#include|require|use)\s+([\w.\"'<>/@*-]+)", re.M),
    "units": re.compile(r"\b(?:class|interface|enum|record|struct|trait|object)\s+([A-Z]\w*)|^\s*(?:def|func|function|fn)\s+(\w+)", re.M),
    "endpoints": re.compile(r"@(Get|Post|Put|Delete|Patch|Request)Mapping\(\s*(?:value\s*=\s*)?\"([^\"]*)\"|\b(?:app|router)\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)", re.M),
    "sql": re.compile(r"\b(SELECT\s.+?\sFROM\s+\w[\w.]*|INSERT\s+INTO\s+\w[\w.]*|UPDATE\s+\w[\w.]*\s+SET|DELETE\s+FROM\s+\w[\w.]*)", re.I | re.S),
}


def analyze_generic(text: str) -> dict:
    out = {"imports": sorted(set(m.group(1).strip("\"'<>") for m in GENERIC["imports"].finditer(text)))[:80],
           "units": sorted(set(a or b for a, b in GENERIC["units"].findall(text)))[:80],
           "endpoints": [], "sql_tables": defaultdict(set)}
    for m in GENERIC["endpoints"].finditer(text):
        out["endpoints"].append((m.group(1) or m.group(3) or "").upper() + " " + (m.group(2) or m.group(4) or ""))
    for m in GENERIC["sql"].finditer(text):
        for crud, t in sql_tables(m.group(1)):
            out["sql_tables"][t].add(crud)
    out["sql_tables"] = {k: "".join(sorted(v, key="CRUD".index)) for k, v in out["sql_tables"].items()}
    out["loc"] = sum(1 for l in text.splitlines() if l.strip())
    return out


# --------------------------------------------------------------------------- scan

def read_text(p: Path) -> str | None:
    try:
        data = p.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def excluded(rel: str, patterns) -> bool:
    parts = rel.split("/")
    for pat in patterns:
        if any(fnmatch.fnmatch(part, pat) for part in parts) or fnmatch.fnmatch(rel, pat):
            return True
    return False


def scan(src: Path, excludes) -> dict:
    inv = {
        "meta": {"source_root": str(src.resolve()), "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "tool": "legacy-code-analysis/inventory.py", "tool_version": "1.0.0"},
        "files": [], "programs": {}, "copybooks": {}, "jobs": {}, "procs": {}, "screens": {}, "transactions": {},
        "cics_files": {}, "tables": {}, "indexes": [], "ims": {}, "unresolved": [], "summary": {},
    }
    for root, dirs, files in os.walk(src):
        dirs[:] = sorted(d for d in dirs if not excluded(d, excludes))
        for fn in sorted(files):
            p = Path(root) / fn
            rel = p.relative_to(src).as_posix()
            if excluded(rel, excludes) or fn.startswith("."):
                continue
            text = read_text(p)
            ftype = "binary" if text is None else classify(p, text[:20000])
            entry = {"path": rel, "type": ftype, "lines": text.count("\n") + 1 if text else 0}
            inv["files"].append(entry)
            if text is None:
                continue
            name = p.stem.upper()
            try:
                if ftype == "cobol":
                    a = analyze_cobol(p, text)
                    a["path"], a["language"] = rel, "COBOL"
                    pid = a["program_id"] or name
                    if pid in inv["programs"]:
                        pid = f"{pid}@{rel}"
                    inv["programs"][pid] = a
                elif ftype == "copybook":
                    a = analyze_copybook(text)
                    a["path"] = rel
                    inv["copybooks"].setdefault(name, a)
                elif ftype == "dclgen":
                    a = analyze_ddl(re.sub(r"EXEC\s+SQL\s+DECLARE\s+([A-Z0-9_.]+)\s+TABLE", r"CREATE TABLE \1", text, flags=re.I).replace("END-EXEC", ";"))
                    inv["copybooks"].setdefault(name, {"path": rel, "dclgen_tables": list(a["tables"])})
                    for t, d in a["tables"].items():
                        inv["tables"].setdefault(t, dict(d, path=rel, source="dclgen"))
                elif ftype in ("jcl", "proc"):
                    a = analyze_jcl(text)
                    a["path"] = rel
                    if ftype == "jcl" or a["job"]:
                        inv["jobs"][a["job"] or name] = a
                    for pn in a["procs_defined"] or ([name] if ftype == "proc" else []):
                        inv["procs"][pn] = a
                elif ftype == "bms":
                    a = analyze_bms(text)
                    a["path"] = rel
                    inv["screens"][a["mapset"] or name] = a
                elif ftype == "csd":
                    a = analyze_csd(text)
                    inv["transactions"].update({k: {"program": v, "path": rel} for k, v in a["transactions"].items()})
                    inv["cics_files"].update({k: {"dsn": v, "path": rel} for k, v in a["files"].items()})
                elif ftype in ("ddl", "sql"):
                    a = analyze_ddl(text)
                    for t, d in a["tables"].items():
                        inv["tables"][t] = dict(d, path=rel, source="ddl")
                    inv["indexes"].extend(dict(i, path=rel) for i in a["indexes"])
                    if ftype == "sql" and not a["tables"]:
                        g = analyze_generic(text)
                        if g["sql_tables"]:
                            inv["programs"][name] = dict(g, path=rel, language="SQL")
                elif ftype in ("ims-dbd", "ims-psb"):
                    inv["ims"][name] = dict(analyze_ims(text, ftype), path=rel, kind=ftype)
                elif ftype in PROGRAM_TYPES:
                    a = analyze_generic(text)
                    a["path"], a["language"] = rel, ftype
                    key = name if name not in inv["programs"] else f"{name}@{rel}"
                    inv["programs"][key] = a
            except Exception as e:  # never let one odd file stop the scan
                entry["error"] = f"{type(e).__name__}: {e}"
    resolve(inv)
    return inv


def resolve(inv: dict):
    progs, cps = inv["programs"], inv["copybooks"]
    known_system = re.compile(r"^(DFH|DSN|CEE|IGZ|ILBO|SQL|CBLTDLI|MQ|IEF|IEB|IDC|ICE|SORT|IKJ|IRX|DFS|CMQ|CSQ)", re.I)
    utility_pgms = {"IDCAMS", "IEFBR14", "IEBGENER", "IEBCOPY", "SORT", "ICETOOL", "DFSORT", "IKJEFT01", "IKJEFT1B", "DSNUTILB", "DFSRRC00", "SYNCSORT", "ADRDSSU", "FTP", "BPXBATCH", "IEHPROGM", "SDSF", "DFHCSDUP", "DSNTIAUL", "DSNTEP2", "DSNTEP4", "DSNUPROC"}
    unresolved = []
    called_by = defaultdict(set)
    # table-driven dispatch (XCTL PROGRAM(OPT-PGMNAME(WS-OPTION))): candidates are the program names that appear
    # as VALUE literals in the program or its copybooks (menu option tables)
    for pid, p in progs.items():
        keep = []
        for d in p.get("dynamic_calls", []):
            if "(" not in d["variable"]:
                keep.append(d)
                continue
            lits = set(p.get("literals", []))
            for c in p.get("copies", []):
                lits |= set(cps.get(c, {}).get("literals", []))
            cands = sorted(l for l in lits if l in progs and l != pid)
            if not cands:
                keep.append(d)
                continue
            key = "link" if d.get("via") == "LINK" else "calls" if d.get("via") == "CALL" else "xctl"
            p[key] = sorted(set(p.get(key, [])) | set(cands))
            p.setdefault("dynamic_resolved", []).append({"variable": d["variable"], "via": d.get("via", "XCTL"), "line": d["line"],
                                                         "candidates": cands, "method": "table-driven (VALUE literals in program/copybooks)"})
        p["dynamic_calls"] = keep
    for pid, p in progs.items():
        for c in p.get("copies", []):
            if c not in cps and not known_system.match(c):
                unresolved.append({"kind": "copybook", "name": c, "from": pid})
        for k in ("calls", "xctl", "link"):
            for c in p.get(k, []):
                called_by[c].add(pid)
                if c not in progs and not known_system.match(c):
                    unresolved.append({"kind": "program", "name": c, "from": pid, "via": k})
        for d in p.get("dynamic_calls", []):
            unresolved.append({"kind": "dynamic-call", "name": d["variable"], "from": pid, "line": d["line"]})
    for j, job in inv["jobs"].items():
        for s in job["steps"]:
            if s.get("pgm"):
                called_by[s["pgm"]].add("JOB:" + j)
                if s["pgm"] not in progs and s["pgm"] not in utility_pgms and not known_system.match(s["pgm"]):
                    unresolved.append({"kind": "program", "name": s["pgm"], "from": "JOB:" + j, "via": "EXEC PGM"})
            if s.get("proc") and s["proc"] not in inv["procs"]:
                unresolved.append({"kind": "proc", "name": s["proc"], "from": "JOB:" + j})
            # IKJEFT01 / DSN RUN PROGRAM(x) in SYSTSIN is not visible here; flagged by the skill.
    for t, d in inv["transactions"].items():
        if d.get("program"):
            called_by[d["program"]].add("TRAN:" + t)
    for pid, p in progs.items():
        p["called_by"] = sorted(called_by.get(pid, []))
        p["entry_point"] = any(c.startswith(("TRAN:", "JOB:")) for c in p["called_by"]) or not p["called_by"]
    # dedupe unresolved
    seen, uniq = set(), []
    for u in unresolved:
        k = (u["kind"], u["name"], u["from"])
        if k not in seen:
            seen.add(k)
            uniq.append(u)
    inv["unresolved"] = uniq
    counts = defaultdict(int)
    for f in inv["files"]:
        counts[f["type"]] += 1
    inv["summary"] = {
        "files_by_type": dict(sorted(counts.items(), key=lambda x: -x[1])),
        "programs": len(progs), "copybooks": len(cps), "jobs": len(inv["jobs"]), "screens": len(inv["screens"]),
        "transactions": len(inv["transactions"]), "tables": len(inv["tables"]), "unresolved": len(uniq),
        "total_loc": sum(p.get("loc", 0) for p in progs.values()),
    }


# --------------------------------------------------------------------------- reports

def mid(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


LIBRARY_DSN = re.compile(r"(LOADLIB|DBRMLIB|PROCLIB|PARMLIB|MACLIB|COPYLIB|\bSDSN\w*|\.LOAD$|\.CNTL$|\.SCEE\w*|\.SDFH\w*)", re.I)


def crud_matrix(inv: dict):
    """Return {program: {resource: CRUD}} for tables, CICS files and batch datasets."""
    rows = defaultdict(dict)
    for pid, p in inv["programs"].items():
        for t, c in p.get("sql_tables", {}).items():
            rows[pid]["DB2:" + t] = c
        for f, c in p.get("cics_files", {}).items():
            dsn = inv["cics_files"].get(f, {}).get("dsn")
            rows[pid]["FILE:" + f + (f" ({dsn})" if dsn else "")] = c
        for f, c in p.get("batch_files", {}).items():
            rows[pid]["DD:" + f] = c
    for j, job in inv["jobs"].items():
        for s in job["steps"]:
            if not s.get("pgm"):
                continue
            for dd in s.get("dds", []):
                if dd.get("dsn") and not dd["dsn"].startswith("&&") and not LIBRARY_DSN.search(dd["dsn"]):
                    key = s["pgm"]
                    prev = rows[key].get("DSN:" + dd["dsn"], "")
                    rows[key]["DSN:" + dd["dsn"]] = "".join(sorted(set(prev + dd["crud"]), key="CRUD".index))
    return rows


def git_info(path: Path) -> dict:
    import subprocess

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
    return {"repo_url": re.sub(r"\.git$", "", url), "repo_ref": run("rev-parse", "HEAD"),
            "repo_subdir": os.path.relpath(path.resolve(), Path(top).resolve()).replace(os.sep, "/").lstrip(".")}


def src_link(meta: dict, rel: str, line=None, line2=None, label=None, from_dir: Path = None) -> str:
    """Markdown link to a source file (optionally a line range): repo permalink if known, else relative path."""
    label = label or (f"{rel}:{line}" + (f"-{line2}" if line2 else "") if line else rel)
    url, ref, sub = meta.get("repo_url"), meta.get("repo_ref"), (meta.get("repo_subdir") or "").strip("/")
    anchor = (f"#L{line}" + (f"-L{line2}" if line2 else "")) if line else ""
    if url and ref:
        p = f"{sub}/{rel}" if sub else rel
        if "gitlab" in url:
            href = f"{url}/-/blob/{ref}/{p}" + (f"#L{line}" + (f"-{line2}" if line2 else "") if line else "")
        else:
            href = f"{url}/blob/{ref}/{p}{anchor}"
    else:
        target = Path(meta["source_root"]) / rel
        href = os.path.relpath(target, (from_dir or Path(".")).resolve()).replace(os.sep, "/") + anchor
    return f"[{label}]({href})"


def write_reports(inv: dict, out: Path):
    meta = inv["meta"]
    out = out.resolve()
    pdir = out / "programs"

    def L(rel, line=None, line2=None, label=None, at=None):
        return src_link(meta, rel, line, line2, label, at or out)

    out.mkdir(parents=True, exist_ok=True)
    (out / "programs").mkdir(exist_ok=True)
    (out / "inventory.json").write_text(json.dumps(inv, indent=1, default=list))
    S = inv["summary"]

    # ---- call graph (online + batch)
    g = ["flowchart LR"]
    nodes = set()
    def node(n, shape):
        if n not in nodes:
            nodes.add(n)
            g.append(f"  {mid(n)}{shape}")
    for t, d in sorted(inv["transactions"].items()):
        node("T_" + t, f"([\"TRAN {t}\"])")
        if d.get("program"):
            node(d["program"], f"[\"{d['program']}\"]")
            g.append(f"  {mid('T_' + t)} --> {mid(d['program'])}")
    for pid, p in sorted(inv["programs"].items()):
        node(pid, f"[\"{pid}\"]")
        for c in p.get("xctl", []):
            node(c, f"[\"{c}\"]"); g.append(f"  {mid(pid)} -. XCTL .-> {mid(c)}")
        for c in p.get("link", []):
            node(c, f"[\"{c}\"]"); g.append(f"  {mid(pid)} -- LINK --> {mid(c)}")
        for c in p.get("calls", []):
            node(c, f"[\"{c}\"]"); g.append(f"  {mid(pid)} -- CALL --> {mid(c)}")
    for j, job in sorted(inv["jobs"].items()):
        pg = [s["pgm"] for s in job["steps"] if s.get("pgm") and s["pgm"] in inv["programs"]]
        if pg:
            node("J_" + j, f"[/\"JOB {j}\"/]")
            for pgm in dict.fromkeys(pg):
                g.append(f"  {mid('J_' + j)} --> {mid(pgm)}")
    (out / "callgraph.mmd").write_text("\n".join(g) + "\n")

    # ---- CRUD matrix
    cm = crud_matrix(inv)
    lines = ["# CRUD matrix", "", "Program (rows) × data resource. C=create R=read U=update D=delete. DB2 = SQL table, FILE = CICS file (dataset), DD = batch file by ddname, DSN = dataset in JCL (from DISP).", ""]
    for pid in sorted(cm):
        lines.append(f"- **{pid}**: " + ", ".join(f"`{r}` {c}" for r, c in sorted(cm[pid].items())))
    (out / "crud-matrix.md").write_text("\n".join(lines) + "\n")

    # ---- data dictionary
    dd = ["# Data dictionary", "", "## DB2 tables", ""]
    for t, d in sorted(inv["tables"].items()):
        dd.append(f"### {t}  \nSource: {L(d.get('path'))} ({d.get('source')}); PK: {', '.join(d['primary_key']) or '—'}")
        for fk in d["foreign_keys"]:
            dd.append(f"FK {', '.join(fk['columns'])} → {fk['references']}" + (f" ({', '.join(fk['ref_columns'])})" if fk.get("ref_columns") else "")
                      + (f" ON DELETE {fk['on_delete']} (business rule candidate)" if fk.get("on_delete") else "") + "  ")
        dd += ["", "| Column | Type | Null |", "|---|---|---|"]
        dd += [f"| {c['name']} | {c['type']} | {'Y' if c['nullable'] else 'N'} |" for c in d["columns"]]
        dd.append("")
    dd += ["## Record layouts (copybooks)", "", "Suggested DB2 / Java types are mechanical defaults from the PIC clause; confirm with the data owner.", ""]
    for c, d in sorted(inv["copybooks"].items()):
        f = d.get("fields") or []
        if not any("pic" in x for x in f):
            continue
        dd += [f"### {c}  \nSource: {L(d['path'])}", "", "| Lvl | Field | PIC | Usage | Occurs | Redefines | DB2 | Java |", "|---|---|---|---|---|---|---|---|"]
        for x in f:
            dd.append(f"| {x['level']:02d} | {x['name']} | {x.get('pic', '')} | {x.get('usage', '')} | {x.get('occurs', '')} | {x.get('redefines', '')} | {x.get('db2', '')} | {x.get('java', '')} |")
        if d.get("conditions88"):
            dd.append("")
            dd.append("88-levels (candidate enumerations / business rules): " + "; ".join(f"`{k['name']}` = {k['values']}" for k in d["conditions88"]))
        dd.append("")
    (out / "data-dictionary.md").write_text("\n".join(dd) + "\n")

    # ---- screens
    sc = ["# Screens (BMS)", "", "Role: input = user-enterable (UNPROT), output = program-filled, label = literal text.", ""]
    used_by = defaultdict(set)
    for pid, p in inv["programs"].items():
        for m in p.get("maps", []):
            used_by[str(m.get("mapset"))].add(pid)
    for ms, d in sorted(inv["screens"].items()):
        sc.append(f"## Mapset {ms}  \nSource: {L(d['path'])}; used by: {', '.join(sorted(used_by.get(ms, []))) or '—'}")
        for m in d["maps"]:
            sc += ["", f"### Map {m['map']} (size {m.get('size')})", "", "| Field | Role | Pos | Len | Attributes | Initial |", "|---|---|---|---|---|---|"]
            for f in m["fields"]:
                if f["role"] == "label" and not f.get("initial"):
                    continue
                sc.append(f"| {f['name'] or ''} | {f['role']} | {f['pos']} | {f['length']} | {f['attrb']} | {(f.get('initial') or '')[:40]} |")
        sc.append("")
    (out / "screens.md").write_text("\n".join(sc) + "\n")

    # ---- batch flows
    bf = ["# Batch jobs", ""]
    for j, job in sorted(inv["jobs"].items()):
        bf.append(f"## {j}  \nSource: {L(job['path'])}")
        flow = ["```mermaid", "flowchart TD"]
        prev = None
        for s in job["steps"]:
            if "control" in s:
                continue
            sid = mid(j + "_" + (s["step"] or str(s["line"])))
            what = s.get("pgm") or ("PROC " + (s.get("proc") or "?"))
            flow.append(f"  {sid}[\"{s['step']}: {what}\"]")
            if prev:
                flow.append(f"  {prev} --> {sid}")
            prev = sid
            for d in s["dds"]:
                if d.get("dsn") and not d["dsn"].startswith("&&") and not LIBRARY_DSN.search(d["dsn"]):
                    did = mid("D_" + d["dsn"])
                    flow.append(f"  {did}[(\"{d['dsn']}\")]")
                    flow.append(f"  {did} --> {sid}" if d["crud"] == "R" else f"  {sid} -- {d['crud']} --> {did}")
        flow.append("```")
        if prev:
            bf += [""] + flow
        bf.append("")
    (out / "batch-flows.md").write_text("\n".join(bf) + "\n")

    # ---- per-program cards
    for pid, p in sorted(inv["programs"].items()):
        c = [f"# {pid}", "", f"- Source: {L(p['path'], at=pdir)} ({p.get('language')}, {p.get('loc', 0)} code lines)",
             f"- Called by: {', '.join(p.get('called_by', [])) or '— (no caller found: entry point or dead code)'}"]
        for k, label in (("xctl", "XCTL to"), ("link", "LINK to"), ("calls", "CALLs"), ("copies", "Copybooks"), ("transids", "Next TRANSID"), ("commarea", "COMMAREA")):
            if p.get(k):
                c.append(f"- {label}: {', '.join(p[k])}")
        if p.get("maps"):
            c.append("- Screens: " + ", ".join(sorted({f"{m['mapset']}/{m['map']}" for m in p['maps']})))
        for k, label in (("sql_tables", "DB2 tables"), ("cics_files", "CICS files"), ("batch_files", "Batch files (ddname)")):
            if p.get(k):
                c.append(f"- {label}: " + ", ".join(f"{n} [{v}]" for n, v in sorted(p[k].items())))
        if p.get("dli"):
            c.append(f"- IMS DL/I calls: {len(p['dli'])}")
        if p.get("mq"):
            c.append("- MQ: " + ", ".join(sorted({m['api'] for m in p['mq']})))
        if p.get("endpoints"):
            c.append("- Endpoints: " + ", ".join(p["endpoints"]))
        if "decisions" in p:
            c.append(f"- Complexity proxy: {p['decisions']} decisions (IF/EVALUATE/WHEN), {p['computations']} computations, {len(p.get('paragraphs', []))} paragraphs")
        if p.get("dynamic_resolved"):
            c.append("- Dynamic transfers resolved from MOVE/VALUE (verify): " + "; ".join(
                f"{d['via']} {d['variable']}@L{d['line']} → {', '.join(d['candidates'])}" for d in p["dynamic_resolved"]))
        if p.get("dynamic_calls"):
            c.append("- Dynamic calls (resolve manually; subscripted = table-driven menu): " + ", ".join(f"{d['variable']}@{d['line']}" for d in p["dynamic_calls"]))
        if p.get("paragraphs"):
            c += ["", "## Paragraphs (line → PERFORMs)", ""]
            for para in p["paragraphs"]:
                tg = p.get("performs", {}).get(para["name"], [])
                c.append(f"- `{para['name']}` {L(p['path'], para['line'], label='L' + str(para['line']), at=pdir)}" + (f" → {', '.join(tg)}" if tg else ""))
        if p.get("conditions88"):
            c += ["", "## 88-level conditions (candidate rules / enumerations)", ""]
            c += [f"- `{k['name']}` = {k['values']} ({L(p['path'], k['line'], label='L' + str(k['line']), at=pdir)})" for k in p["conditions88"]]
        if p.get("messages"):
            c += ["", "## User/diagnostic messages (candidate validation rules)", ""]
            c += [f"- {L(p['path'], m['line'], label='L' + str(m['line']), at=pdir)} in `{m['paragraph']}`: \"{m['text']}\" → {m['target']}" for m in p["messages"]]
        if p.get("evidence"):
            c += ["", "## Evidence (reference → lines)", ""]
            c += [f"- {k}: {', '.join(L(p['path'], x, label='L' + str(x), at=pdir) for x in v)}" for k, v in sorted(p["evidence"].items())]
        (out / "programs" / f"{mid(pid)}.md").write_text("\n".join(c) + "\n")

    # ---- summary
    sm = ["# System inventory", "", f"Source root: `{inv['meta']['source_root']}`  ", f"Scanned: {inv['meta']['scanned_at']}", "",
          "## Counts", "", "| Item | Count |", "|---|---|"]
    for k in ("programs", "copybooks", "jobs", "screens", "transactions", "tables", "unresolved", "total_loc"):
        sm.append(f"| {k} | {S[k]} |")
    sm += ["", "Files by type: " + ", ".join(f"{k}={v}" for k, v in S["files_by_type"].items()), "",
           "## Entry points", "", "### Online transactions", ""]
    sm += [f"- `{t}` → {d.get('program')}" for t, d in sorted(inv["transactions"].items())] or ["- none found (no CSD); infer from RETURN TRANSID in program cards"]
    sm += ["", "### Batch jobs", ""]
    sm += [f"- `{j}`: " + " → ".join(s.get("pgm") or ("PROC " + str(s.get("proc"))) for s in job["steps"] if "control" not in s) for j, job in sorted(inv["jobs"].items())]
    sm += ["", "## Programs", "", "| Program | Lang | LOC | Decisions | Called by | Data |", "|---|---|---|---|---|---|"]
    for pid, p in sorted(inv["programs"].items(), key=lambda x: -x[1].get("loc", 0)):
        data = list(p.get("sql_tables", {})) + list(p.get("cics_files", {})) + list(p.get("batch_files", {}))
        sm.append(f"| [{pid}](programs/{mid(pid)}.md) | {p.get('language')} | {p.get('loc', 0)} | {p.get('decisions', '')} | {', '.join(p.get('called_by', []))[:60]} | {', '.join(data)[:60]} |")
    sm += ["", "## Unresolved references", "", "Each one is a gap to close before the requirements are complete (missing source, system module, or dynamic call).", ""]
    sm += [f"- {u['kind']} `{u['name']}` from {u['from']}" + (f" (L{u['line']})" if u.get('line') else "") for u in inv["unresolved"]] or ["- none"]
    sm += ["", "## Other outputs", "", "- `callgraph.mmd`: transaction/job → program graph (Mermaid)", "- `crud-matrix.md`, `data-dictionary.md`, `screens.md`, `batch-flows.md`", "- `programs/*.md`: one card per program with line evidence"]
    (out / "inventory.md").write_text("\n".join(sm) + "\n")


# --------------------------------------------------------------------------- slice

def slice_inv(inv: dict, roots, depth: int) -> dict:
    progs = inv["programs"]
    start = []
    for root in (r.upper() for r in roots):
        if root in inv["transactions"]:
            start.append(inv["transactions"][root]["program"])
        elif root in inv["jobs"]:
            start += [s["pgm"] for s in inv["jobs"][root]["steps"] if s.get("pgm") in progs]
        elif root in progs:
            start.append(root)
        else:
            sys.exit(f"'{root}' is not a known program, transaction or job")
    seen, frontier, outside = set(), [(p, 0) for p in start], set()
    while frontier:
        p, d = frontier.pop()
        if p in seen or p not in progs:
            continue
        seen.add(p)
        targets = [c for k in ("xctl", "link", "calls") for c in progs[p].get(k, [])]
        # don't expand through menus/dispatchers (unless named as a root): they reach the whole application
        if d < depth and (len(set(targets)) <= 5 or p in start):
            for c in targets:
                cp = progs.get(c, {})
                hub = len(cp.get("called_by", [])) > 3 or len({x for k in ("xctl", "link", "calls") for x in cp.get(k, [])}) > 5
                # XCTL back to a shared menu/sign-on is navigation out of the slice, not part of it
                if c in progs[p].get("xctl", []) and hub and c not in start:
                    outside.add(c)
                    continue
                frontier.append((c, d + 1))
    files, copies, tables, mapsets, cfiles = set(), set(), set(), set(), set()
    for p in seen:
        pr = progs[p]
        files.add(pr["path"])
        for c in pr.get("copies", []):
            copies.add(c)
            if c in inv["copybooks"]:
                files.add(inv["copybooks"][c]["path"])
        tables |= set(pr.get("sql_tables", {}))
        cfiles |= set(pr.get("cics_files", {}))
        for m in pr.get("maps", []):
            mapsets.add(m.get("mapset"))
            if m.get("mapset") in inv["screens"]:
                files.add(inv["screens"][m["mapset"]]["path"])
    for t in tables:
        if t in inv["tables"]:
            files.add(inv["tables"][t]["path"])
    # resources the slice owns: datasets behind its CICS files, its tables; then every job that runs a slice
    # program or touches those datasets (define/load/backup jobs belong to the capability too)
    dsns = {inv["cics_files"][f]["dsn"] for f in cfiles if inv["cics_files"].get(f, {}).get("dsn")}
    bases = {re.sub(r"\.(VSAM\.)?(KSDS|AIX|PATH|ESDS|RRDS)$", "", d) for d in dsns}
    jobs = set()
    for j, job in inv["jobs"].items():
        for s in job["steps"]:
            hit = s.get("pgm") in seen or any(
                dd.get("dsn") and (dd["dsn"] in dsns or any(dd["dsn"].startswith(b) for b in bases)) for dd in s.get("dds", []))
            if not hit and s.get("pgm") == "IDCAMS":
                text = ""  # IDCAMS SYSIN is instream: match dataset names in the job source
                try:
                    text = (Path(inv["meta"]["source_root"]) / job["path"]).read_text(errors="ignore").upper()
                except OSError:
                    pass
                hit = any(b in text for b in bases)
            if hit:
                jobs.add(j)
                files.add(job["path"])
                break
    trans = sorted(t for t, d in inv["transactions"].items() if d.get("program") in seen)
    for t in trans:
        files.add(inv["transactions"][t]["path"])
    for f in cfiles:
        if f in inv["cics_files"]:
            files.add(inv["cics_files"][f]["path"])
    return {"roots": [r.upper() for r in roots], "programs": sorted(seen), "navigates_outside": sorted(outside - seen), "transactions": trans, "jobs": sorted(jobs),
            "copybooks": sorted(copies), "tables": sorted(tables), "cics_files": sorted(cfiles), "datasets": sorted(dsns),
            "mapsets": sorted(x for x in mapsets if x), "files_to_read": sorted(files)}


def domains(inv: dict, hub_share: float) -> list:
    """Candidate business domains: programs that share data resources or call each other.

    Hubs are ignored so they don't glue everything together: a resource used by more than
    `hub_share` of the programs, and programs (menus, sign-on) that more than 3 others transfer to.
    """
    progs = [p for p, v in inv["programs"].items() if v.get("language") == "COBOL" or v.get("sql_tables")]
    parent = {p: p for p in progs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        if a in parent and b in parent:
            parent[find(a)] = find(b)

    cm = crud_matrix(inv)
    users = defaultdict(set)
    for p in progs:
        for r in cm.get(p, {}):
            users[r].add(p)
    limit = max(2, int(len(progs) * hub_share))
    for r, ps in users.items():
        if len(ps) <= limit:
            ps = sorted(ps)
            for q in ps[1:]:
                union(ps[0], q)
    indeg = defaultdict(int)
    for p in progs:
        for k in ("xctl", "link", "calls"):
            for c in inv["programs"][p].get(k, []):
                indeg[c] += 1
    for p in progs:
        targets = [c for k in ("xctl", "link", "calls") for c in inv["programs"][p].get(k, [])]
        if len(set(targets)) > 5:  # dispatcher/menu: linking it would glue unrelated domains together
            continue
        for c in targets:
            if indeg[c] <= 3:
                union(p, c)
    groups = defaultdict(list)
    for p in progs:
        groups[find(p)].append(p)
    out = []
    for ps in sorted(groups.values(), key=len, reverse=True):
        res = sorted({r for p in ps for r in cm.get(p, {}) if len(users[r]) <= limit})
        trans = sorted(t for t, d in inv["transactions"].items() if d.get("program") in ps)
        jobs = sorted({j for j, job in inv["jobs"].items() for s in job["steps"] if s.get("pgm") in ps})
        out.append({"programs": sorted(ps), "resources": res, "transactions": trans, "jobs": jobs})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--src", required=True)
    s.add_argument("--out", default="docs/analysis")
    s.add_argument("--exclude", nargs="*", default=[])
    s.add_argument("--repo-url", help="web URL of the repository for permalinks (auto-detected from git)")
    s.add_argument("--repo-ref", help="commit SHA or tag to pin links to (auto-detected: HEAD)")
    s.add_argument("--repo-subdir", help="path of --src inside the repository (auto-detected)")
    sl = sub.add_parser("slice")
    sl.add_argument("--inventory", default="docs/analysis/inventory.json")
    sl.add_argument("--root", required=True, nargs="+", help="one or more transaction IDs, job names or program names")
    sl.add_argument("--depth", type=int, default=4)
    dm = sub.add_parser("domains")
    dm.add_argument("--inventory", default="docs/analysis/inventory.json")
    dm.add_argument("--hub-share", type=float, default=0.25, help="ignore resources used by more than this share of programs")
    a = ap.parse_args()
    if a.cmd == "domains":
        inv = json.loads(Path(a.inventory).read_text())
        groups = domains(inv, a.hub_share)
        lines = ["# Candidate domains", "", "Clusters of programs that share data or call each other (hubs ignored). "
                 "Name each one with the business (e.g. 'Account maintenance') and use it as a BRD capability or document slice.", ""]
        for i, g in enumerate(groups, 1):
            lines += [f"## D{i:02d} ({len(g['programs'])} programs)", "",
                      f"- Programs: {', '.join(g['programs'])}",
                      f"- Transactions: {', '.join(g['transactions']) or '—'}",
                      f"- Jobs: {', '.join(g['jobs']) or '—'}",
                      f"- Shared data: {', '.join(g['resources']) or '—'}", ""]
        out = Path(a.inventory).parent / "domains.md"
        out.write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
        return
    if a.cmd == "scan":
        src = Path(a.src)
        if not src.is_dir():
            sys.exit(f"--src {src} is not a directory")
        inv = scan(src, DEFAULT_EXCLUDES + a.exclude)
        g = git_info(src)
        for k in ("repo_url", "repo_ref", "repo_subdir"):
            v = getattr(a, k) if getattr(a, k) is not None else g.get(k, "")
            inv["meta"][k] = v
        if g and not a.repo_ref:
            import subprocess
            dirty = subprocess.run(["git", "-C", str(src), "status", "--porcelain", "."], capture_output=True, text=True).stdout.strip()
            if dirty:
                print("WARN: source has uncommitted changes; permalinks point at HEAD and may not match the scanned lines")
        out = Path(a.out)
        write_reports(inv, out)
        print(json.dumps(inv["summary"], indent=1))
        print(f"\nWrote {out}/inventory.json, inventory.md, callgraph.mmd, crud-matrix.md, data-dictionary.md, screens.md, batch-flows.md, programs/")
    else:
        inv = json.loads(Path(a.inventory).read_text())
        print(json.dumps(slice_inv(inv, a.root, a.depth), indent=1))


if __name__ == "__main__":
    main()
