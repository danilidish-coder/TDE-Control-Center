"""Native, external functional check of the packaged EXE using synthetic data only."""
from __future__ import annotations
import argparse
from datetime import datetime
from zipfile import ZipFile
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time


def wait_for(operation, timeout=45):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            value = operation()
            if value: return value
        except Exception as exc:
            last = exc
        time.sleep(0.25)
    raise TimeoutError(f'Readiness condition failed: {last}')


def exercise(executable, output):
    if os.name != 'nt': raise RuntimeError('This check requires a real Windows desktop')
    import psutil
    from pywinauto import Desktop
    from openpyxl import load_workbook
    output.mkdir(parents=True, exist_ok=True)
    report = {'status': 'failed', 'exe_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(), 'steps': []}
    process = None
    window = None
    with tempfile.TemporaryDirectory(prefix='tde-modular-exe-') as scratch:
        target = Path(scratch) / executable.name
        shutil.copy2(executable, target)
        database = target.parent / '.tde_runtime' / 'tde_control_center.sqlite3'
        def query(sql):
            connection = sqlite3.connect(database, timeout=5)
            try:
                return connection.execute(sql).fetchall()
            finally:
                connection.close()
        def button(parent, text):
            controls = [control for control in parent.descendants()
                        if control.element_info.control_type in ('Button', 'RadioButton')
                        and control.is_visible() and control.window_text() == text]
            if len(controls) != 1:
                raise AssertionError(f'Expected one visible button {text!r}, got {len(controls)}')
            controls[0].click_input()
        def dialog_window(title):
            # Qt owned dialogs may be nested in the UIA tree rather than desktop
            # children. Resolve the actual HWND first, then wrap that exact window.
            native = Desktop(backend='win32').window(title=title, process=window.process_id()).wrapper_object()
            return Desktop(backend='uia').window(handle=native.handle).wrapper_object()
        def save_diagnostics():
            native = [{'title': item.window_text(), 'handle': item.handle, 'pid': item.process_id(), 'class': item.class_name()}
                      for item in Desktop(backend='win32').windows() if item.process_id() == window.process_id()]
            controls = [{'title': item.window_text(), 'role': item.element_info.control_type, 'visible': item.is_visible(), 'rectangle': str(item.rectangle())}
                        for item in window.descendants()]
            (output / 'ui-diagnostics.json').write_text(json.dumps({'native_windows': native, 'uia_controls': controls}, ensure_ascii=False, indent=2) + chr(10), encoding='utf-8')
        try:
            environment = dict(os.environ)
            environment.pop('QT_QPA_PLATFORM', None)
            process = subprocess.Popen([str(target)], cwd=target.parent, env=environment)
            def main_window():
                for candidate in Desktop(backend='uia').windows(title_re='.*ΚΕΝΤΡΟ.*|.*Τ.Δ.Ε. ΚΡΥΣΤΑΛΛΟΠΗΓΗΣ.*'):
                    try:
                        if Path(psutil.Process(candidate.process_id()).exe()).resolve() == target.resolve() and candidate.is_visible():
                            return candidate
                    except (psutil.Error, OSError):
                        continue
            window = wait_for(main_window)
            window.set_focus()
            wait_for(lambda: database.exists() and query('SELECT COUNT(*) FROM shifts') == [(0,)])
            report['steps'].append('native window and fresh SQLite initialized')
            window.capture_as_image().save(str(output / 'startup.png'))
            button(window, 'ΕΝΑΡΞΗ ΒΑΡΔΙΑΣ')
            dialog = wait_for(lambda: dialog_window('Έναρξη Βάρδιας'))
            edits = [control for control in dialog.descendants(control_type='Edit') if control.is_visible()]
            if len(edits) != 4: raise AssertionError(f'Expected four shift fields, got {len(edits)}')
            for control, text in zip(edits, ['TEST-RANK', '999999', 'PHASE1', 'VALIDATION']):
                control.set_edit_text(text)
            button(dialog, 'ΕΝΑΡΞΗ')
            wait_for(lambda: query("SELECT officer_name, status FROM shifts") == [('PHASE1 VALIDATION', 'OPEN')])
            report['steps'].append('shift created through native UI and verified in SQLite')
            # Fill by the visible label/field geometry, without modifying the
            # frozen program or writing synthetic rows behind its UI.
            for label, value in [('ΕΠΩΝΥΜΟ', 'PHASE2-SYNTHETIC'), ('ΟΝΟΜΑ', 'TEST')]:
                labels = [c for c in window.descendants(control_type='Text')
                          if c.is_visible() and c.window_text() == label]
                if len(labels) != 1:
                    raise AssertionError(f'Expected one field label {label!r}, got {len(labels)}')
                rectangle = labels[0].rectangle()
                y = (rectangle.top + rectangle.bottom) // 2
                candidates = [c for c in window.descendants(control_type='Edit')
                              if c.is_visible() and c.is_enabled()
                              and c.rectangle().left >= rectangle.right
                              and c.rectangle().top <= y <= c.rectangle().bottom]
                if not candidates:
                    raise AssertionError(f'Missing editable field beside {label!r}')
                min(candidates, key=lambda c: c.rectangle().left).set_edit_text(value)
            button(window, 'ΚΑΤΑΧΩΡΙΣΗ')
            confirmation = wait_for(lambda: dialog_window('Επιβεβαίωση'))
            yes = [b for b in confirmation.descendants(control_type='Button')
                   if b.window_text().replace('&', '').lower() in ('yes', 'ναι')]
            if len(yes) != 1:
                raise AssertionError('Missing fine-entry confirmation')
            yes[0].click_input()
            completed = wait_for(lambda: dialog_window('Ολοκληρώθηκε'))
            buttons = [b for b in completed.descendants(control_type='Button')
                       if b.is_visible() and b.window_text().replace('&', '').lower() in ('ok', 'εντάξει')]
            if len(buttons) != 1:
                raise AssertionError('Missing successful fine-entry acknowledgement')
            buttons[0].click_input()
            wait_for(lambda: query('SELECT COUNT(*) FROM fines') == [(1,)])
            report['steps'].append('synthetic fine entered and confirmed through frozen native UI')
            for label in ['ΑΡΝΗΣΕΙΣ', 'ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ', 'ΠΕΡΙΟΔΙΚΑ', 'ΑΡΧΕΙΟ - ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ', 'ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ', 'ΠΡΟΣΤΙΜΑ']:
                button(window, label)
            report['steps'].append('all six navigation buttons exercised')
            button(window, 'ΚΛΕΙΣΙΜΟ ΒΑΡΔΙΑΣ')
            confirmation = wait_for(lambda: dialog_window('Κλείσιμο βάρδιας'))
            yes = [b for b in confirmation.descendants(control_type='Button') if b.window_text().replace('&', '').lower() in ('yes', 'ναι')]
            if len(yes) != 1: raise AssertionError('Missing close-shift confirmation button')
            yes[0].click_input()
            wait_for(lambda: query('SELECT status FROM shifts') == [('CLOSED',)])
            workbook = wait_for(lambda: next((target.parent / '.tde_runtime' / 'archive').rglob('*.xlsx'), None))
            book = wait_for(lambda: load_workbook(workbook))
            if 'Ημερήσια Δραστηριότητα' not in book.sheetnames:
                raise AssertionError('Daily activity workbook missing expected worksheet')
            start, end = query('SELECT started_at, ended_at FROM shifts')[0]
            for timestamp in (start, end):
                if datetime.fromisoformat(timestamp).strftime('%d/%m/%Y %H:%M') not in book['Ημερήσια Δραστηριότητα']['A7'].value:
                    raise AssertionError('Frozen Excel report did not use recorded shift times')
            book.close()
            documents = list((target.parent / '.tde_runtime' / 'archive').rglob('*.docx'))
            if not documents:
                raise AssertionError('Frozen executable did not produce the fines DOCX')
            from lxml import etree
            found_fine = False
            for document in documents:
                with ZipFile(document) as package:
                    if package.testzip() is not None:
                        raise AssertionError('Invalid frozen DOCX ZIP')
                    root = etree.fromstring(package.read('word/document.xml'))
                    text = ''.join(root.xpath('//*[local-name()="t"]/text()'))
                    if 'PHASE2-SYNTHETIC' in text:
                        found_fine = True
                        for timestamp in (start, end):
                            if datetime.fromisoformat(timestamp).strftime('%H:%M') not in text:
                                raise AssertionError('Frozen Word report did not use recorded shift times')
                        if 'ΕΝΕΡΓΗ ΒΑΡΔΙΑ' in text:
                            raise AssertionError('Closed frozen report still marked active')
            if not found_fine:
                raise AssertionError('Synthetic fine missing from frozen DOCX')
            backups = list((target.parent / '.tde_runtime' / 'backup').glob('*.sqlite3'))
            if not backups:
                raise AssertionError('Frozen executable did not create a backup')
            for backup in backups:
                connection = sqlite3.connect(backup)
                try:
                    if connection.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                        raise AssertionError('Frozen backup integrity failure')
                    if connection.execute('SELECT COUNT(*) FROM fines').fetchone() != (1,):
                        raise AssertionError('Frozen backup lost the synthetic fine')
                finally:
                    connection.close()
            report['steps'].append('frozen DOCX, Excel recorded times and SQLite backup contents verified')
            if query('PRAGMA integrity_check') != [('ok',)] or query('PRAGMA foreign_key_check'):
                raise AssertionError('SQLite integrity failure')
            wait_for(lambda: query('SELECT COUNT(*) FROM pending_jobs WHERE resolved_at IS NULL') == [(0,)])
            report['steps'].append('shift closed, daily XLSX generated, SQLite integrity and pending jobs verified')
            report['status'] = 'passed'
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
            if window is not None:
                try:
                    save_diagnostics()
                    window.capture_as_image().save(str(output / 'failure.png'))
                except Exception: pass
            raise
        finally:
            (output / 'functional-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            if process is not None:
                try:
                    parent = psutil.Process(process.pid)
                    children = parent.children(recursive=True)
                    for child in reversed(children):
                        try: child.kill()
                        except psutil.Error: pass
                    try: parent.kill()
                    except psutil.Error: pass
                    psutil.wait_procs(children + [parent], timeout=10)
                except psutil.NoSuchProcess: pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('executable', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    exercise(args.executable.resolve(), args.output.resolve())


if __name__ == '__main__': main()
