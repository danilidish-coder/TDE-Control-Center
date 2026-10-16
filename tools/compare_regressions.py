"""Compare real pytest outcomes without reclassifying historical failures."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def read(path):
    result = {}
    for case in ET.parse(path).iter('testcase'):
        parts = case.get('classname').split('.')
        start = next((i for i, part in enumerate(parts) if part.startswith('test_')), 0)
        key = '.'.join(parts[start:]) + '::' + case.get('name')
        state = 'passed'
        for tag in ('failure', 'error', 'skipped'):
            if case.find(tag) is not None: state = tag
        if key in result: raise ValueError(f'Duplicate testcase: {key}')
        result[key] = state
    if not result: raise ValueError('No tests executed')
    return result


def compare(baseline, current):
    missing = sorted(set(baseline) - set(current))
    changed = {key: [state, current.get(key)] for key, state in baseline.items() if current.get(key) != state}
    new = {key: state for key, state in current.items() if key not in baseline}
    bad_new = {key: state for key, state in new.items() if state != 'passed'}
    summary = {
        'baseline_tests': len(baseline), 'current_tests': len(current),
        'historical_failures': sorted(key for key, state in baseline.items() if state in ('failure', 'error')),
        'missing': missing, 'changed_outcomes': changed,
        'new_tests_passed': sum(state == 'passed' for state in new.values()),
        'new_tests_not_passed': bad_new,
        'compatible': not (missing or changed or bad_new),
    }
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare(read(args.baseline), read(args.current))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['compatible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
