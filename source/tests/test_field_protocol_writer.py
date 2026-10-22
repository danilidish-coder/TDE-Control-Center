"""Exercise the real COM writer contract with a recording Excel adapter, not Office."""
from datetime import datetime
from types import SimpleNamespace,ModuleType
import sys
from app.features.receipts.workbook import ProtocolWorkbookWriter


def test_real_writer_preserves_six_financial_fields_and_neutral_signature_shapes(tmp_path,monkeypatch):
    import app.features.receipts.workbook as module
    cells={};ranges={};shapes={}
    def item(mapping,key):
        return mapping.setdefault(key,SimpleNamespace())
    def shape(name):
        return shapes.setdefault(name,SimpleNamespace(TextFrame2=SimpleNamespace(TextRange=SimpleNamespace(Text=''))))
    ws=SimpleNamespace(Cells=lambda r,c:item(cells,(r,c)),Range=lambda name:item(ranges,name),
        Columns=lambda name:item(ranges,'column-'+name),Shapes=SimpleNamespace(Count=0,Item=shape),
        PageSetup=SimpleNamespace(),Calculate=lambda:None)
    ws.Range('A12:G40').ClearContents=lambda:None
    calls=[]
    wb=SimpleNamespace(Worksheets=lambda name:ws,Save=lambda:calls.append('save'),Close=lambda **kw:calls.append('close'))
    excel=SimpleNamespace(Workbooks=SimpleNamespace(Open=lambda **kw:wb),Quit=lambda:calls.append('quit'))
    pythoncom=ModuleType('pythoncom');pythoncom.CoInitialize=lambda:None;pythoncom.CoUninitialize=lambda:None
    win32com=ModuleType('win32com');client=ModuleType('win32com.client');client.DispatchEx=lambda name:excel;win32com.client=client
    for name,m in [('pythoncom',pythoncom),('win32com',win32com),('win32com.client',client)]:monkeypatch.setitem(sys.modules,name,m)
    monkeypatch.setattr(module.platform,'system',lambda:'Windows')
    template=tmp_path/'synthetic.xlsx';template.write_bytes(b'SYNTHETIC COM ADAPTER ONLY')
    rows=[dict(protocol_no=f'P{i}',amount=600,payment_type=method,measure=f'M{i}',paravolo=f'E{i}') for i,method in enumerate(('ΜΕΤΡΗΤΑ','ePARAVOLO','Δ.Ε. ΤΥΠΟΥ-Α','UNKNOWN',''))]
    output=ProtocolWorkbookWriter(template).write(tmp_path/'out.xlsx',rows,collector_name='COLLECTOR',receiver_name='RECEIVER',handover_at=datetime(2026,10,23,2,13))
    assert output.is_file() and calls==['save','close','quit']
    for index,row in enumerate(rows,12):
        assert [cells[index,c].Value for c in range(2,7)]==[row['protocol_no'],row['amount'],row['payment_type'] or 'EISPRAXI',row['measure'],row['paravolo']]
    assert [cells[r,7].Value for r in range(12,17)]==['payment','eparavolo','detypa','unclassified','unclassified']
    assert ranges['column-G'].Hidden
    assert cells[41,3].Formula=='=SUMIF(G12:G16,"payment",C12:C16)'
    assert cells[44,3].Formula=='=SUM(C12:C16)'
    assert 'μη ταξινομημένες' in cells[44,2].Value
    assert ws.PageSetup.PrintArea=='$A$1:$F$54'
    assert 'COLLECTOR' in shapes['TextBox 3'].TextFrame2.TextRange.Text
    assert 'RECEIVER' in shapes['TextBox 5'].TextFrame2.TextRange.Text
    for item in shapes.values():
        assert 'ηλεκτρον' not in item.TextFrame2.TextRange.Text.lower()
        assert '23/10/2026 02:13' in item.TextFrame2.TextRange.Text
