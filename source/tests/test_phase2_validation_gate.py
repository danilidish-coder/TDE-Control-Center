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
