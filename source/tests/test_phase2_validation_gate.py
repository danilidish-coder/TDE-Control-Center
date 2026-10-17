import importlib.util
from pathlib import Path
import sys


def test_phase2_gate_only_accepts_the_twelve_documented_corrections(monkeypatch):
    tools = Path(__file__).resolve().parents[2] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    spec = importlib.util.spec_from_file_location('phase2_gate', tools / 'compare_phase2_regressions.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = {key: 'failure' for key in module.EXPECTED} | {'original_pass': 'passed'}
    current = {key: 'passed' for key in baseline} | {'new': 'passed'}
    assert module.compare_phase2(baseline, current)['compatible']
    for state in ('failure', 'error', 'skipped'):
        assert not module.compare_phase2(baseline, current | {'original_pass': state})['compatible']
        assert not module.compare_phase2(baseline, current | {'new': state})['compatible']
        for key in module.EXPECTED:
            assert not module.compare_phase2(baseline, current | {key: state})['compatible']
    assert not module.compare_phase2(baseline, {k: v for k, v in current.items() if k != 'original_pass'})['compatible']
    assert not module.compare_phase2(baseline | {'unexpected_old_failure': 'failure'}, current | {'unexpected_old_failure': 'passed'})['compatible']


def test_behavior_gate_rejects_any_difference_except_one_active_preview_annotation(monkeypatch):
    from copy import deepcopy
    tools = Path(__file__).resolve().parents[2] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    from compare_phase2_behavior import compare_behavior, PREVIEW, PART, ANNOTATION
    for preview in (PREVIEW, PREVIEW.replace('/', chr(92))):
        baseline = {'database': {'shift': 'closed'}, 'documents': {preview: {PART: '<t>signature</t>'}, 'archive/fines.docx': {PART: '<t>original final</t>'}}}
        current = deepcopy(baseline)
        current['documents'][preview][PART] = '<t>signature' + ANNOTATION + '</t>'
        assert compare_behavior(baseline, current)['compatible']
        assert not compare_behavior(baseline, baseline)['compatible']
        changed = deepcopy(current)
        changed['database']['shift'] = 'changed'
        assert not compare_behavior(baseline, changed)['compatible']
        changed = deepcopy(current)
        changed['documents']['archive/fines.docx'][PART] += ANNOTATION
        assert not compare_behavior(baseline, changed)['compatible']
        changed = deepcopy(current)
        changed['documents'][preview][PART] += ANNOTATION
        assert not compare_behavior(baseline, changed)['compatible']
        changed = deepcopy(current)
        changed['documents'][preview][PART] = '<t>changed signature' + ANNOTATION + '</t>'
        assert not compare_behavior(baseline, changed)['compatible']


def test_frozen_backup_check_distinguishes_initial_snapshot_from_completed_shift(tmp_path, monkeypatch):
    import sqlite3
    from datetime import datetime
    import pytest
    tools = Path(__file__).resolve().parents[2] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    from exercise_windows_exe import verify_backup_snapshots
    from app.core.db import Database
    from app.features.fines.documents import FineEntry
    from app.features.fines.service import FineService
    from app.infrastructure.backup import backup_database
    import app.core.paths as paths
    monkeypatch.setattr(paths, 'runtime_root', lambda: tmp_path)
    db = Database(tmp_path / 'data.sqlite3')
    initial = backup_database(db.path)
    start, end = datetime(2026, 10, 17, 23, 43), datetime(2026, 10, 18, 3, 19)
    db.start_shift('SYNTHETIC', start)
    FineService(db).add_fine('IMPOSITION', FineEntry(date='17/10/2026', surname='PHASE2-SYNTHETIC', name='TEST', amount=600), start)
    db.close_shift(end)
    final = backup_database(db.path)
    args = (initial.parent, start.isoformat(timespec='seconds'), end.isoformat(timespec='seconds'))
    assert verify_backup_snapshots(*args) == {'initial_snapshots': 1, 'closed_shift_snapshots': 1}
    connection = sqlite3.connect(final)
    try:
        connection.execute('DELETE FROM fines')
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(AssertionError, match='Unexpected frozen backup'):
        verify_backup_snapshots(*args)
    final.unlink()
    with pytest.raises(AssertionError, match='Both the initial and completed'):
        verify_backup_snapshots(*args)
    initial.write_bytes(b'truncated SQLite')
    with pytest.raises(sqlite3.DatabaseError):
        verify_backup_snapshots(*args)
