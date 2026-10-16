"""Native, external functional check of the packaged EXE using synthetic data only."""
from __future__ import annotations
import argparse
from datetime import datetime
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
            with sqlite3.connect(database, timeout=5) as connection:
                return connection.execute(sql).fetchall()
        def button(parent, text):
            control = parent.child_window(title=text, control_type='Button').wrapper_object()
            control.click_input()
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
            dialog = wait_for(lambda: Desktop(backend='uia').window(title='Έναρξη Βάρδιας').wrapper_object())
            edits = [control for control in dialog.descendants(control_type='Edit') if control.is_visible()]
            if len(edits) != 4: raise AssertionError(f'Expected four shift fields, got {len(edits)}')
            for control, text in zip(edits, ['TEST-RANK', '999999', 'PHASE1', 'VALIDATION']):
                control.set_edit_text(text)
            button(dialog, 'ΕΝΑΡΞΗ')
            wait_for(lambda: query("SELECT officer_name, status FROM shifts") == [('PHASE1 VALIDATION', 'OPEN')])
            report['steps'].append('shift created through native UI and verified in SQLite')
            for label in ['ΑΡΝΗΣΕΙΣ', 'ΗΜΕΡΗΣΙΑ ΔΡΑΣΤΗΡΙΟΤΗΤΑ', 'ΠΕΡΙΟΔΙΚΑ', 'ΑΡΧΕΙΟ - ΑΝΑΖΗΤΗΣΗ ΠΡΟΣΩΠΟΥ', 'ΕΙΣΠΡΑΞΕΙΣ ΠΡΟΣΤΙΜΩΝ', 'ΠΡΟΣΤΙΜΑ']:
                button(window, label)
            report['steps'].append('all six navigation buttons exercised')
            button(window, 'ΚΛΕΙΣΙΜΟ ΒΑΡΔΙΑΣ')
            confirmation = wait_for(lambda: Desktop(backend='uia').window(title='Κλείσιμο βάρδιας').wrapper_object())
            yes = [b for b in confirmation.descendants(control_type='Button') if b.window_text().replace('&', '').lower() in ('yes', 'ναι')]
            if len(yes) != 1: raise AssertionError('Missing close-shift confirmation button')
            yes[0].click_input()
            wait_for(lambda: query('SELECT status FROM shifts') == [('CLOSED',)])
            workbook = wait_for(lambda: next((target.parent / '.tde_runtime' / 'archive').rglob('*.xlsx'), None))
            book = load_workbook(workbook)
            if 'Ημερήσια Δραστηριότητα' not in book.sheetnames:
                raise AssertionError('Daily activity workbook missing expected worksheet')
            book.close()
            if query('PRAGMA integrity_check') != [('ok',)] or query('PRAGMA foreign_key_check'):
                raise AssertionError('SQLite integrity failure')
            if query('SELECT COUNT(*) FROM pending_jobs WHERE resolved_at IS NULL') != [(0,)]:
                raise AssertionError('Archive jobs remain pending')
            report['steps'].append('shift closed, daily XLSX generated, SQLite integrity and pending jobs verified')
            report['status'] = 'passed'
        except Exception as exc:
            report['error'] = f'{type(exc).__name__}: {exc}'
            if window is not None:
                try: window.capture_as_image().save(str(output / 'failure.png'))
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
