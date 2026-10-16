"""Compare fixed synthetic business data and document content across source trees."""
from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile
from lxml import etree
from openpyxl import load_workbook

sys.path.insert(0, sys.argv[1])
import app.core.paths as paths
from app.core.db import Database
from app.docgen.fines_report import FineEntry
from app.docgen.refusals import RefusalEntry
from app.services.fines import FineService
from app.services.refusals import RefusalService
from app.services.daily_activity import DailyActivityService

class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None): return cls(2026, 10, 16, 18, 0, 0)

for name, module in list(sys.modules.items()):
    if name.startswith('app.') and getattr(module, 'datetime', None) is datetime:
        module.datetime = FixedDatetime

with tempfile.TemporaryDirectory(prefix='tde-behavior-') as scratch:
    runtime = Path(scratch)
    paths.runtime_root = lambda: runtime
    db = Database(runtime / 'data.sqlite3')
    shift = db.start_shift('PHASE1 OFFICER', datetime(2026, 10, 16, 10), officer_agms='999999', officer_rank_short='TEST', officer_rank_full='TEST RANK')
    fines, refusals, daily = FineService(db), RefusalService(db), DailyActivityService(db)
    fines.add_fine('IMPOSITION', FineEntry(date='16/10/2026', surname='SUBJECT-A', name='SYNTHETIC', birth_date='01/01/1990', amount=600, imposition_protocol='IMP-1'), datetime(2026, 10, 16, 11))
    fines.add_fine('PAYMENT', FineEntry(date='16/10/2026', surname='SUBJECT-B', name='SYNTHETIC', amount=1200, responsible='TEST COLLECTOR', collection_method='eΠαράβολο', collection_protocol='COL-1'), datetime(2026, 10, 16, 12))
    refusals.add_refusal(RefusalEntry(aa='1', year='2026', protocol_prefix='456', protocol_no='900', date='16-10-2026', time='13:00', sex='M', surname='SUBJECT-C', name='SYNTHETIC', birth_date='04-05-1990', passport='TEST-999', issue_date='01-01-2025', reason='A-ΕΛΛΕΙΨΗ ΕΓΚΥΡΟΥ ΤΑΞ. ΕΓΓΡΑΦΟΥ', language='ΑΓΓΛΙΚΑ'), datetime(2026, 10, 16, 13))
    daily.save_manual(shift, {})
    db.close_shift(datetime(2026, 10, 16, 18))
    fines.generate_shift_report(shift, archive=True)
    refusals.generate_vas(shift, archive=True)
    daily.generate(shift, archive=True)
    summary = daily.summary_for_shift(shift)
    documents = {}
    for path in sorted(runtime.rglob('*.docx')):
        with ZipFile(path) as package:
            documents[str(path.relative_to(runtime))] = {
                name: etree.tostring(etree.fromstring(package.read(name)), method='c14n').decode('utf-8')
                for name in sorted(package.namelist()) if name.startswith('word/') and name.endswith('.xml')
            }
    workbooks = {}
    for path in sorted(runtime.rglob('*.xlsx')):
        book = load_workbook(path)
        workbooks[str(path.relative_to(runtime))] = {
            sheet.title: {
                'cells': [[cell.coordinate, cell.value, cell.number_format, cell.style_id] for row in sheet for cell in row if cell.value is not None],
                'merged': sorted(str(area) for area in sheet.merged_cells.ranges),
            }
            for sheet in book
        }
        book.close()
    connection = db.connect()
    try:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        database = {table: [dict(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid')] for table in tables}
    finally:
        connection.close()
    data = {'summary': summary, 'database': database, 'documents': documents, 'workbooks': workbooks}
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, default=str).replace(str(runtime).replace('\\', '\\\\'), '<RUNTIME>')
    Path(sys.argv[2]).write_text(encoded + '\n', encoding='utf-8')
    print(f'Captured {len(tables)} SQLite tables, {len(documents)} Word documents, {len(workbooks)} workbooks')
