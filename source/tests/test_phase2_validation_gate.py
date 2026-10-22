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


def test_native_field_selection_uses_recorded_small_windows_desktop_geometry(monkeypatch):
    from types import SimpleNamespace
    import pytest
    tools = Path(__file__).resolve().parents[2] / 'tools'
    monkeypatch.syspath_prepend(str(tools))
    from exercise_windows_exe import select_labeled_edit
    def rect(left, top, right, bottom): return SimpleNamespace(left=left, top=top, right=right, bottom=bottom)
    def edit(name, box, enabled=True):
        return SimpleNamespace(name=name, rectangle=lambda: box, is_visible=lambda: True, is_enabled=lambda: enabled)
    # Actual rectangles from run 39014785312: several 48px fields overlap when
    # the runner desktop compresses grid rows to 18px. A shared center is unsafe.
    fields = [edit('date', rect(543,343,684,391)), edit('protocol', rect(543,361,684,409)), edit('paravolo', rect(543,379,684,427),False), edit('surname', rect(543,396,684,444)), edit('name', rect(543,414,684,462)), edit('birth', rect(543,432,684,480)), edit('right_column', rect(855,396,998,444))]
    assert select_labeled_edit(rect(386,396,531,406), fields).name == 'surname'
    assert select_labeled_edit(rect(386,414,531,424), fields).name == 'name'
    with pytest.raises(AssertionError, match='Missing editable'):
        select_labeled_edit(rect(386,200,531,210), fields)
    with pytest.raises(AssertionError, match='Ambiguous'):
        select_labeled_edit(rect(386,396,531,406), fields + [fields[3]])


def test_native_editable_combo_uses_recorded_inset_geometry_not_neighbor(monkeypatch):
    from types import SimpleNamespace
    tools=Path(__file__).resolve().parents[2]/'tools'
    monkeypatch.syspath_prepend(str(tools))
    from exercise_windows_exe import select_labeled_edit
    def rect(l,t,r,b):return SimpleNamespace(left=l,top=t,right=r,bottom=b)
    def edit(name,box):return SimpleNamespace(name=name,rectangle=lambda:box,is_visible=lambda:True,is_enabled=lambda:True)
    # Actual UIA rectangles from failed run 39835119592. Method label midpoint
    # 401 is one pixel ABOVE the combo's Edit. Previous selector chose measure.
    controls=[edit('measure',rect(855,361,998,409)),edit('method',rect(866,402,929,438)),edit('protocol',rect(855,414,998,462)),edit('officer',rect(855,432,998,480))]
    assert select_labeled_edit(rect(698,396,843,406),controls).name=='method'
    assert select_labeled_edit(rect(698,414,843,424),controls).name=='protocol'
    assert select_labeled_edit(rect(698,432,843,441),controls).name=='officer'
