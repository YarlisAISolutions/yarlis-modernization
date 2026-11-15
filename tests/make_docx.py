#!/usr/bin/env python3
"""Write a small synthetic .docx for the convert tests: python3 tests/make_docx.py <out.docx>

Covers what convert.py has to get right: headings found by style name (a localized style id), an outline-level heading,
bold/italic/link runs, bullet and numbered lists from numbering.xml, a table with a merged cell and a pipe,
tracked changes (deleted text dropped, inserted text kept) and a content control.
"""
import sys
import zipfile

NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')


def p(inner, style=None, num=None, outline=None):
    ppr = ""
    if style or num or outline is not None:
        ppr = "<w:pPr>"
        if style:
            ppr += f'<w:pStyle w:val="{style}"/>'
        if num:
            ppr += f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>'
        if outline is not None:
            ppr += f'<w:outlineLvl w:val="{outline}"/>'
        ppr += "</w:pPr>"
    return f"<w:p>{ppr}{inner}</w:p>"


def r(text, bold=False, italic=False):
    rpr = ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "")
    return f'<w:r>{f"<w:rPr>{rpr}</w:rPr>" if rpr else ""}<w:t xml:space="preserve">{text}</w:t></w:r>'


def cell(text, span=1):
    tcpr = f'<w:tcPr><w:gridSpan w:val="{span}"/></w:tcPr>' if span > 1 else ""
    return f"<w:tc>{tcpr}{p(r(text))}</w:tc>"


BODY = "".join([
    p(r("Account Rules"), style="Title"),
    p(r("Overview"), style="berschrift1"),
    p(r("Staff ") + r("must", bold=True) + r(" update ") + r("credit limits", italic=True) + r(" daily. See ")
      + '<w:hyperlink r:id="rIdLink">' + r("the wiki") + "</w:hyperlink>" + r(".")),
    p(r("Limits"), outline=1),
    p(r("Checks"), style="berschrift1"),
    p(r("Limit is positive"), num=("1", "0")),
    p(r("Limit under 999,999"), num=("1", "1")),
    p(r("Validate the account"), num=("2", "0")),
    p(r("Save the change"), num=("2", "0")),
    p(r("Kept ") + '<w:del w:id="1" w:author="a"><w:r><w:delText>removed </w:delText></w:r></w:del>'
      + '<w:ins w:id="2" w:author="a">' + r("added") + "</w:ins>"),
    '<w:sdt><w:sdtPr/><w:sdtContent>' + p(r("Inside a content control")) + "</w:sdtContent></w:sdt>",
    "<w:tbl>"
    + "<w:tr>" + cell("Field") + cell("Rule") + cell("Note") + "</w:tr>"
    + "<w:tr>" + cell("LIMIT") + cell("a | b", span=2) + "</w:tr>"
    + "</w:tbl>",
    p(""),
])

DOCUMENT = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{BODY}</w:body></w:document>'
STYLES = (f'<?xml version="1.0" encoding="UTF-8"?><w:styles {NS}>'
          '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/></w:style>'
          '<w:style w:type="paragraph" w:styleId="berschrift1"><w:name w:val="heading 1"/></w:style>'
          '</w:styles>')
NUMBERING = (f'<?xml version="1.0" encoding="UTF-8"?><w:numbering {NS}>'
             '<w:abstractNum w:abstractNumId="10"><w:lvl w:ilvl="0"><w:numFmt w:val="bullet"/></w:lvl>'
             '<w:lvl w:ilvl="1"><w:numFmt w:val="bullet"/></w:lvl></w:abstractNum>'
             '<w:abstractNum w:abstractNumId="20"><w:lvl w:ilvl="0"><w:numFmt w:val="decimal"/></w:lvl></w:abstractNum>'
             '<w:num w:numId="1"><w:abstractNumId w:val="10"/></w:num>'
             '<w:num w:numId="2"><w:abstractNumId w:val="20"/></w:num>'
             '</w:numbering>')
RELS = ('<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rIdLink" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
        'Target="https://wiki.example.com/limits" TargetMode="External"/></Relationships>')

# The Markdown convert.py must produce for the document above (after its marker line and a blank line).
EXPECTED = """# Account Rules

# Overview

Staff **must** update _credit limits_ daily. See [the wiki](https://wiki.example.com/limits).

## Limits

# Checks

- Limit is positive
  - Limit under 999,999

1. Validate the account
1. Save the change

Kept added

Inside a content control

| Field | Rule | Note |
|---|---|---|
| LIMIT | a \\| b |  |
"""

if __name__ == "__main__":
    with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in [("word/document.xml", DOCUMENT), ("word/styles.xml", STYLES),
                           ("word/numbering.xml", NUMBERING), ("word/_rels/document.xml.rels", RELS)]:
            z.writestr(zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)), data)
