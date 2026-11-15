#!/usr/bin/env python3
"""Convert Word (.docx) and PDF inputs to Markdown next to the original, so agents can read and cite them.

    convert.py [paths ...] [--force] [--quiet]        (also `docver.py convert`, `l2m docs convert`)

`spec.docx` becomes `spec.docx.md` and `spec.pdf` becomes `spec.pdf.md` in the same folder. Each output starts with a
marker naming its source and the source's sha256, so a re-run rewrites only what changed and never overwrites a
Markdown file it did not write (unless --force). The output holds no dates, so the same input always gives the same file.

- .docx: read with the standard library (zipfile + XML): headings (from styles.xml), bullet and numbered lists
  (from numbering.xml), tables, links, bold and italic. Headers, footers, footnotes, comments and images are left out.
- .pdf: needs `pdftotext` from Poppler on PATH. There is no reliable PDF text extraction in the standard library
  (compressed streams, font encodings, ToUnicode maps), so without the tool the file is skipped with the install command.
- .doc (Word 97-2003) is not read: save it as .docx.

Exit codes: 0 everything converted or already up to date; 1 at least one file was skipped (missing tool, unreadable
file, or a hand-written Markdown file in the way).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

VERSION = "1"  # bump when the output format changes, so existing conversions are rewritten
SKIP_DIRS = {".git", "node_modules", "target", "build", "dist", ".idea", ".vscode", "__pycache__", ".venv"}
MAX_XML_BYTES = 64 * 1024 * 1024  # uncompressed document.xml; larger means a zip bomb or not a document
PDF_TIMEOUT = 120
MARKER = re.compile(r"^<!-- l2m convert v(\S+): generated from (.+) \(sha256 ([0-9a-f]{12})\)")
PDF_INSTALL = ("PDF conversion needs pdftotext from Poppler, which is not on PATH. Install it "
               "(macOS: brew install poppler; Debian/Ubuntu: sudo apt install poppler-utils; "
               "Fedora: sudo dnf install poppler-utils; Windows: choco install poppler or scoop install poppler), "
               "then run the command again")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


class ConvertError(Exception):
    pass


# --- docx ---------------------------------------------------------------------------------------------------------

def _on(el) -> bool:
    """A w:b / w:i toggle: present and not switched off."""
    return el is not None and el.get(W + "val", "true").lower() not in ("0", "false", "off", "none")


def _read_xml(z: zipfile.ZipFile, name: str):
    try:
        info = z.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_XML_BYTES:
        raise ConvertError(f"{name} is {info.file_size} bytes uncompressed, over the {MAX_XML_BYTES} byte limit")
    return ET.fromstring(z.read(info))


class Docx:
    def __init__(self, path: Path):
        try:
            z = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            raise ConvertError("not a valid .docx (zip) file")
        with z:
            doc = _read_xml(z, "word/document.xml")
            if doc is None:
                raise ConvertError("no word/document.xml inside: not a Word document")
            styles = _read_xml(z, "word/styles.xml")
            numbering = _read_xml(z, "word/numbering.xml")
            rels = _read_xml(z, "word/_rels/document.xml.rels")
        self.body = doc.find(W + "body")
        self.styles = {}  # styleId -> (name, basedOn, outlineLvl, numPr)
        for s in (styles.findall(W + "style") if styles is not None else []):
            ppr = s.find(W + "pPr")
            name = s.find(W + "name")
            based = s.find(W + "basedOn")
            outline = ppr.find(W + "outlineLvl") if ppr is not None else None
            self.styles[s.get(W + "styleId")] = (
                (name.get(W + "val") if name is not None else "").strip().lower(),
                based.get(W + "val") if based is not None else None,
                int(outline.get(W + "val")) if outline is not None and (outline.get(W + "val") or "").isdigit() else None,
                ppr.find(W + "numPr") if ppr is not None else None,
            )
        self.formats = {}  # (numId, ilvl) -> numFmt
        if numbering is not None:
            abstract = {}
            for a in numbering.findall(W + "abstractNum"):
                abstract[a.get(W + "abstractNumId")] = {
                    lvl.get(W + "ilvl"): (lvl.find(W + "numFmt").get(W + "val") if lvl.find(W + "numFmt") is not None else "bullet")
                    for lvl in a.findall(W + "lvl")}
            for n in numbering.findall(W + "num"):
                ref = n.find(W + "abstractNumId")
                for ilvl, fmt in abstract.get(ref.get(W + "val") if ref is not None else None, {}).items():
                    self.formats[(n.get(W + "numId"), ilvl)] = fmt
        self.links = {}
        for r in (rels.findall(REL + "Relationship") if rels is not None else []):
            if r.get("TargetMode") == "External" or r.get("Type", "").endswith("/hyperlink"):
                self.links[r.get("Id")] = r.get("Target")

    def _style_chain(self, style_id):
        seen = set()
        while style_id and style_id in self.styles and style_id not in seen:
            seen.add(style_id)
            yield self.styles[style_id]
            style_id = self.styles[style_id][1]

    def _heading(self, ppr) -> int:
        """Heading level 1-6 from the paragraph's outline level or its style (by name, so localized ids still work)."""
        if ppr is None:
            return 0
        outline = ppr.find(W + "outlineLvl")
        if outline is not None and (outline.get(W + "val") or "").isdigit() and int(outline.get(W + "val")) < 9:
            return min(int(outline.get(W + "val")) + 1, 6)
        style = ppr.find(W + "pStyle")
        for name, _, lvl, _ in self._style_chain(style.get(W + "val") if style is not None else None):
            if name == "title":
                return 1
            m = re.fullmatch(r"heading ?(\d)", name)
            if m:
                return min(max(int(m.group(1)), 1), 6)
            if lvl is not None and lvl < 9:
                return min(lvl + 1, 6)
        return 0

    def _list(self, ppr):
        """(depth, ordered, numId) for a list paragraph, else None."""
        if ppr is None:
            return None
        numpr = ppr.find(W + "numPr")
        if numpr is None:
            style = ppr.find(W + "pStyle")
            numpr = next((n for *_, n in self._style_chain(style.get(W + "val") if style is not None else None) if n is not None), None)
        if numpr is None:
            return None
        num, ilvl = numpr.find(W + "numId"), numpr.find(W + "ilvl")
        num_id = num.get(W + "val") if num is not None else None
        if num_id in (None, "0"):  # numId 0 switches numbering off
            return None
        level = ilvl.get(W + "val") if ilvl is not None else "0"
        fmt = self.formats.get((num_id, level), "bullet")
        return (int(level) if level.isdigit() else 0, fmt not in ("bullet", "none"), num_id)

    def _runs(self, el, out, link=None):
        """Collect (text, bold, italic, link) segments in document order. Deleted text is dropped, inserted text kept."""
        for c in el:
            tag = c.tag
            if tag in (W + "del", W + "moveFrom", W + "pPr", W + "rPr"):
                continue
            if tag == W + "r":
                rpr = c.find(W + "rPr")
                bold = _on(rpr.find(W + "b")) if rpr is not None else False
                italic = _on(rpr.find(W + "i")) if rpr is not None else False
                for t in c:
                    if t.tag == W + "t":
                        out.append((t.text or "", bold, italic, link))
                    elif t.tag in (W + "tab", W + "ptab"):
                        out.append((" ", bold, italic, link))
                    elif t.tag in (W + "br", W + "cr") and t.get(W + "type") not in ("page", "column"):
                        out.append(("\n", False, False, link))
                    elif t.tag == W + "noBreakHyphen":
                        out.append(("-", bold, italic, link))
            elif tag == W + "hyperlink":
                self._runs(c, out, self.links.get(c.get(R + "id")) or link)
            elif tag == W + "sdt":
                content = c.find(W + "sdtContent")
                if content is not None:
                    self._runs(content, out, link)
            else:  # w:ins, w:smartTag, w:fldSimple, w:customXml, w:moveTo ...
                self._runs(c, out, link)

    def _inline(self, p) -> str:
        segs = []
        self._runs(p, segs)
        merged = []  # adjacent segments with the same format become one, so markers don't split words
        for text, bold, italic, link in segs:
            if merged and merged[-1][1:] == (bold, italic, link):
                merged[-1] = (merged[-1][0] + text, bold, italic, link)
            else:
                merged.append((text, bold, italic, link))
        parts = []
        for text, bold, italic, link in merged:
            lead = text[: len(text) - len(text.lstrip())]
            core = text.strip()
            trail = text[len(lead) + len(core):] if core else ""
            if not core:
                parts.append(text)
                continue
            core = _escape(core)
            mark = ("**" if bold else "") + ("_" if italic else "")
            core = f"{mark}{core}{mark[::-1]}"
            if link:
                core = f"[{core}]({link.replace(' ', '%20').replace(')', '%29')})"
            parts.append(lead + core + trail)
        return re.sub(r" *\n *", "\n", re.sub(r"[ \t]+", " ", "".join(parts))).strip(" ")

    def _cell(self, tc) -> str:
        lines = []
        for p in tc.iter(W + "p"):  # nested tables are flattened into the cell's text
            text = self._inline(p)
            if text:
                lines.append(text.replace("\n", "<br>"))
        return "<br>".join(lines).replace("|", "\\|")

    def _table(self, tbl) -> str:
        rows = []
        for tr in tbl.findall(W + "tr"):
            row = []
            for tc in tr.findall(W + "tc"):
                tcpr = tc.find(W + "tcPr")
                span = tcpr.find(W + "gridSpan") if tcpr is not None else None
                vmerge = tcpr.find(W + "vMerge") if tcpr is not None else None
                continued = vmerge is not None and vmerge.get(W + "val", "continue") == "continue"
                row.append("" if continued else self._cell(tc))
                width = span.get(W + "val") if span is not None else "1"
                row.extend([""] * (int(width) - 1 if width.isdigit() else 0))
            if row:
                rows.append(row)
        if not rows:
            return ""
        cols = max(len(r) for r in rows)
        rows = [r + [""] * (cols - len(r)) for r in rows]
        line = lambda r: "| " + " | ".join(r) + " |"
        return "\n".join([line(rows[0]), "|" + "---|" * cols] + [line(r) for r in rows[1:]])

    def _blocks(self, parent, out):
        for el in parent:
            if el.tag == W + "p":
                text = self._inline(el)
                if not text.strip():
                    continue
                ppr = el.find(W + "pPr")
                level = self._heading(ppr)
                lst = None if level else self._list(ppr)
                if level:
                    out.append(("block", "#" * level + " " + text.replace("\n", " ")))
                elif lst:
                    depth, ordered, num_id = lst
                    indent = "   " * depth if ordered else "  " * depth
                    marker = "1. " if ordered else "- "
                    out.append(("item:" + num_id, indent + marker + text.replace("\n", "\n" + indent + " " * len(marker))))
                else:
                    out.append(("block", text))
            elif el.tag == W + "tbl":
                table = self._table(el)
                if table:
                    out.append(("block", table))
            elif el.tag == W + "sdt":
                content = el.find(W + "sdtContent")
                if content is not None:
                    self._blocks(content, out)
            elif el.tag in (W + "ins", W + "customXml", W + "smartTag"):
                self._blocks(el, out)

    def markdown(self) -> str:
        blocks = []
        if self.body is not None:
            self._blocks(self.body, blocks)
        out = []
        for i, (kind, text) in enumerate(blocks):
            if out:  # list items stay together; everything else is separated by a blank line
                out.append("\n" if kind.startswith("item:") and blocks[i - 1][0] == kind else "\n\n")
            out.append(text)
        return "".join(out)


def _escape(text: str) -> str:
    """Escape what would otherwise turn plain Word text into Markdown or HTML."""
    text = re.sub(r"([\\`*_\[\]<])", r"\\\1", text)
    return re.sub(r"(?m)^(\s*)([#>+-]|\d+\.)(\s)", r"\1\\\2\3", text)


def docx_to_markdown(path: Path) -> str:
    try:
        return Docx(path).markdown()
    except ET.ParseError as e:
        raise ConvertError(f"broken XML inside the .docx: {e}")


# --- pdf ----------------------------------------------------------------------------------------------------------

def pdf_to_markdown(path: Path) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise ConvertError(PDF_INSTALL)
    try:
        r = subprocess.run([exe, "-enc", "UTF-8", str(path.resolve()), "-"], capture_output=True, timeout=PDF_TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ConvertError(f"pdftotext took longer than {PDF_TIMEOUT}s")
    if r.returncode != 0:
        raise ConvertError(f"pdftotext failed: {r.stderr.decode('utf-8', 'replace').strip() or f'exit {r.returncode}'}")
    pages = r.stdout.decode("utf-8", "replace").replace("\r\n", "\n").split("\f")
    out = []
    for n, page in enumerate(pages, 1):
        paras = [p.strip("\n") for p in re.split(r"\n[ \t]*\n+", page)]
        paras = [re.sub(r"[ \t]+$", "", _escape(p), flags=re.M) for p in paras if p.strip()]
        if paras:
            out.append(f"<!-- page {n} -->\n\n" + "\n\n".join(paras))
    return "\n\n".join(out)


# --- driver -------------------------------------------------------------------------------------------------------

CONVERTERS = {".docx": docx_to_markdown, ".pdf": pdf_to_markdown}


def _walk(path: Path):
    if path.is_file():
        yield path
        return
    for dirpath, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(files):
            yield Path(dirpath) / f


def convert(paths, force=False, log=print):
    """Convert every .docx/.pdf under paths. Returns (converted, up_to_date, skipped) counts."""
    done = fresh = skipped = 0
    for root in paths:
        root = Path(root)
        if not root.exists():
            log(f"skip {root}: not found")
            skipped += 1
            continue
        for src in _walk(root):
            ext = src.suffix.lower()
            if src.name.startswith("~$") or src.name.startswith("."):
                continue  # Word lock files, hidden files
            if ext == ".doc":
                log(f"note {src}: Word 97-2003 .doc is not read; save it as .docx")
                continue
            if ext not in CONVERTERS:
                continue
            dst = src.with_name(src.name + ".md")
            digest = hashlib.sha256(src.read_bytes()).hexdigest()[:12]
            if dst.exists():
                m = MARKER.match(dst.read_text(encoding="utf-8", errors="replace"))
                if not m and not force:
                    log(f"skip {src}: {dst.name} exists and was not written by l2m (use --force to replace it)")
                    skipped += 1
                    continue
                if m and m.group(1) == VERSION and m.group(3) == digest and not force:
                    fresh += 1
                    continue
            try:
                body = CONVERTERS[ext](src)
            except (ConvertError, OSError) as e:
                log(f"skip {src}: {e}")
                skipped += 1
                continue
            header = (f"<!-- l2m convert v{VERSION}: generated from {src.name} (sha256 {digest}). "
                      f"Edit the source document and run `l2m docs convert` again; do not edit this file. -->")
            with open(dst, "w", encoding="utf-8", newline="\n") as f:  # Path.write_text(newline=) needs 3.10
                f.write(f"{header}\n\n{body}\n" if body else f"{header}\n")
            log(f"converted {src} -> {dst}" + ("" if body else " (no text found)"))
            done += 1
    return done, fresh, skipped


def add_arguments(p):
    p.add_argument("paths", nargs="*", default=["docs/inputs"], help="files or folders (default: docs/inputs)")
    p.add_argument("--force", action="store_true", help="rewrite every output, including Markdown files l2m did not write")
    p.add_argument("--quiet", action="store_true", help="no summary line")


def run(a) -> int:
    done, fresh, skipped = convert(a.paths, force=a.force)
    if not a.quiet:
        print(f"{done} converted, {fresh} up to date, {skipped} skipped")
    return 1 if skipped else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(ap)
    sys.exit(run(ap.parse_args()))


if __name__ == "__main__":
    main()
