from dataclasses import replace
from pathlib import Path
from zipfile import ZipFile
import subprocess
import types
from lxml import etree
from app.core.paths import resource_path
from app.features.fines.documents import FineEntry,FineReportEngine
from app.shared.documents.docx_mirror import NS,W,cell_text

BASE='557558b5d25695ecf93c9e50be99f0c67afe7859'

def table(path):
    with ZipFile(path) as z:
        assert z.testzip() is None
        return etree.fromstring(z.read('word/document.xml')).xpath('//w:tbl',namespaces=NS)[0]


def test_receipts_only_style_top_exact_xml_and_all_economic_fields_unchanged(tmp_path):
    # Load the exact approved engine for a real generated before/after comparison.
    code=subprocess.check_output(['git','show',f'{BASE}:source/app/features/fines/documents.py'],text=True,encoding='utf8')
    module=types.ModuleType('approved_fines')
    import sys
    sys.modules[module.__name__]=module
    try:
        exec(compile(code,'approved_fines.py','exec'),module.__dict__)
        entries=[FineEntry(date='22/10/2026',surname='SYNTHETIC',amount=600,responsible='OFFICER')]
        entries += [replace(entries[0],surname=f'RECEIPT-{i}',amount=1200,collection_method='ΕΦΟΡΙΑ',collection_protocol=f'PAY-{i}',paravolo=f'REF-{i}') for i in range(24)]
        before=module.FineReportEngine(resource_path('Anafora_base.docx')).write_entries(tmp_path/'before.docx',entries)
        after=FineReportEngine(resource_path('Anafora_base.docx')).write_entries(tmp_path/'after.docx',entries)
    finally:
        del sys.modules[module.__name__]
    old,new=table(before),table(after)
    oldrows=old.xpath('./w:tr',namespaces=NS);rows=new.xpath('./w:tr',namespaces=NS)
    first=FineReportEngine._find_collection_header(rows)
    assert len(oldrows)==len(rows)
    for a,b in zip(oldrows[:first],rows[:first]):
        assert etree.tostring(a,method='c14n')==etree.tostring(b,method='c14n')
    for a,b in zip(oldrows,rows):
        assert [cell_text(c) for c in a.xpath('./w:tc',namespaces=NS)]==[cell_text(c) for c in b.xpath('./w:tc',namespaces=NS)]
    for row in rows[first:]:
        assert len(row.xpath('./w:tc',namespaces=NS))==11
        assert set(row.xpath('.//w:rPr/w:sz/@w:val',namespaces=NS))=={'16'}
        assert row.xpath('./w:tc/w:tcPr/w:tcMar',namespaces=NS)
    assert etree.tostring(old.find(f'{{{W}}}tblGrid'))==etree.tostring(new.find(f'{{{W}}}tblGrid'))
