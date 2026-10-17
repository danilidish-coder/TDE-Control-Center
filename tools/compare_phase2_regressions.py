"""Require every Phase 1 pass and exactly twelve documented test corrections."""
import argparse
import json
from pathlib import Path

from compare_regressions import compare, read

REPO = Path(__file__).resolve().parents[1]
EXPECTED = frozenset(item['class'].removeprefix('tests.') + '::' + item['test'] for item in json.loads((REPO / 'docs/modular-phase1-baseline.json').read_text(encoding='utf-8')))


def compare_phase2(baseline, current):
    report = compare(baseline, current)
    actual_failures = {key for key, state in baseline.items() if state in ('failure', 'error')}
    corrected = {key for key in EXPECTED if baseline.get(key) == 'failure' and current.get(key) == 'passed'}
    unexpected = {key: states for key, states in report['changed_outcomes'].items() if key not in corrected}
    report.update({
        'documented_historical_corrections': sorted(corrected),
        'baseline_failure_set_matches_phase1': actual_failures == EXPECTED,
        'unexpected_outcome_changes': unexpected,
        'compatible': actual_failures == EXPECTED and corrected == EXPECTED and not (report['missing'] or unexpected or report['new_tests_not_passed']),
    })
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare_phase2(read(args.baseline), read(args.current))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['compatible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
