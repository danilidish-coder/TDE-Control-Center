from __future__ import annotations

import copy
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
XML = "http://www.w3.org/XML/1998/namespace"


def _assign_text(node, value: str) -> None:
    """Assign w:t text using Word's whitespace-preservation rule."""
    node.text = value
    key = f"{{{XML}}}space"
    if value.startswith(" ") or value.endswith(" ") or value.startswith("\t") or value.endswith("\t"):
        node.set(key, "preserve")
    else:
        node.attrib.pop(key, None)


def _extract(docx: Path, folder: Path) -> None:
    with ZipFile(docx) as z:
        z.extractall(folder)


def _pack(folder: Path, docx: Path) -> None:
    docx.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(docx, "w", ZIP_DEFLATED) as z:
        for f in folder.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(folder).as_posix())


def replace_sequence(root, old: str, new: str, *, bold: bool | None = None) -> int:
    """Word-Find-like text replacement across split w:t nodes, without reflowing structure."""
    if not old:
        return 0
    count = 0
    cursor = 0
    while True:
        nodes = root.xpath("//w:t", namespaces=NS)
        texts = [n.text or "" for n in nodes]
        full = "".join(texts)
        pos = full.find(old, cursor)
        if pos < 0:
            break
        end = pos + len(old)
        cur = 0
        si = ei = None
        so = eo = 0
        for i, txt in enumerate(texts):
            nxt = cur + len(txt)
            if si is None and pos < nxt:
                si, so = i, pos - cur
            if si is not None and end <= nxt:
                ei, eo = i, end - cur
                break
            cur = nxt
        if si is None or ei is None:
            break
        s, e = nodes[si], nodes[ei]
        prefix, suffix = (s.text or "")[:so], (e.text or "")[eo:]
        _assign_text(s, prefix + new + (suffix if si == ei else ""))
        if bold is not None:
            run = s.getparent()
            if run.tag == f"{{{W}}}r":
                rpr = run.find(f"{{{W}}}rPr")
                if rpr is None:
                    rpr = etree.Element(f"{{{W}}}rPr")
                    run.insert(0, rpr)
                b = rpr.find(f"{{{W}}}b")
                if bold and b is None:
                    # Keep WordprocessingML run-property order identical to the
                    # original VBA/Word output.  Appending <w:b/> at the end of
                    # <w:rPr> changes LibreOffice glyph rendering by a few edge
                    # pixels even though the visible text is the same.  In the
                    # reference document <w:b/> sits immediately after w:rFonts.
                    b = etree.Element(f"{{{W}}}b")
                    rfonts = rpr.find(f"{{{W}}}rFonts")
                    if rfonts is not None:
                        rpr.insert(rpr.index(rfonts) + 1, b)
                    else:
                        # If rFonts is absent, bold is one of the first character
                        # properties; insert before spacing/size/etc.
                        insert_at = 0
                        for i, child in enumerate(rpr):
                            local = etree.QName(child).localname
                            if local in {"spacing", "w", "kern", "position", "sz", "szCs", "highlight", "color"}:
                                insert_at = i
                                break
                            insert_at = i + 1
                        rpr.insert(insert_at, b)
                elif not bold and b is not None:
                    rpr.remove(b)
        if si != ei:
            for j in range(si + 1, ei):
                _assign_text(nodes[j], "")
            _assign_text(e, suffix)
        count += 1
        # Continue after the replacement, matching Word's Replace All semantics.
        # This also prevents an infinite loop when the replacement is identical
        # to, or contains, the search text.
        cursor = pos + len(new)
    return count


def replace_sequence_occurrence(root, old: str, new: str, occurrence: int) -> bool:
    """Replace exactly one 1-based occurrence across split ``w:t`` nodes.

    Used when the same literal appears more than once in a Word template but each
    occurrence has a different runtime value (for example start/end shift time).
    The surrounding OOXML/run formatting is preserved exactly.
    """
    if not old or occurrence < 1:
        return False
    nodes = root.xpath("//w:t", namespaces=NS)
    texts = [n.text or "" for n in nodes]
    full = "".join(texts)
    start = 0
    pos = -1
    for _ in range(occurrence):
        pos = full.find(old, start)
        if pos < 0:
            return False
        start = pos + len(old)
    end = pos + len(old)
    cur = 0
    si = ei = None
    so = eo = 0
    for i, txt in enumerate(texts):
        nxt = cur + len(txt)
        if si is None and pos < nxt:
            si, so = i, pos - cur
        if si is not None and end <= nxt:
            ei, eo = i, end - cur
            break
        cur = nxt
    if si is None or ei is None:
        return False
    s, e = nodes[si], nodes[ei]
    prefix, suffix = (s.text or "")[:so], (e.text or "")[eo:]
    _assign_text(s, prefix + new + (suffix if si == ei else ""))
    if si != ei:
        for j in range(si + 1, ei):
            _assign_text(nodes[j], "")
        _assign_text(e, suffix)
    return True


def cell_text(tc) -> str:
    return "".join(tc.xpath(".//w:t/text()", namespaces=NS)).strip()


def set_cell_text(tc, text: str) -> None:
    ts = tc.xpath(".//w:t", namespaces=NS)
    if ts:
        ts[0].text = str(text)
        for t in ts[1:]:
            t.text = ""
    else:
        p = tc.find(f"{{{W}}}p")
        if p is None:
            p = etree.SubElement(tc, f"{{{W}}}p")
        r = etree.SubElement(p, f"{{{W}}}r")
        t = etree.SubElement(r, f"{{{W}}}t")
        t.text = str(text)


def clear_cell_text(tc) -> None:
    for t in tc.xpath(".//w:t", namespaces=NS):
        t.text = ""


def make_fines_base(reference_docx: Path, output_docx: Path) -> None:
    """Create a private internal blank base while preserving every row/style from the real report."""
    with tempfile.TemporaryDirectory() as td0:
        td = Path(td0)
        _extract(reference_docx, td)
        xml_path = td / "word" / "document.xml"
        root = etree.fromstring(xml_path.read_bytes())
        table = root.xpath("//w:tbl", namespaces=NS)[0]
        rows = table.xpath("./w:tr", namespaces=NS)
        for ri, row in enumerate(rows):
            if ri in (0, 9):
                continue
            for tc in row.xpath("./w:tc", namespaces=NS):
                clear_cell_text(tc)
        xml_path.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes"))
        _pack(td, output_docx)


def clone_docx_with_xml(source: Path, output: Path, mutator) -> None:
    with tempfile.TemporaryDirectory() as td0:
        td = Path(td0)
        _extract(source, td)
        xml_path = td / "word" / "document.xml"
        root = etree.fromstring(xml_path.read_bytes())
        mutator(root)
        xml_path.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone="yes"))
        _pack(td, output)
