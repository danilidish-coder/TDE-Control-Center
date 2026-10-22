"""Audit the one proven Windows baseline lock race without excusing candidate failures."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from compare_regressions import compare, read

LOCK_TEST='test_concurrency::test_serialized_concurrent_writes'
LOCK_SIGNATURE=('PermissionError', 'WinError 5', '.write.lock', 'self.lock_dir.mkdir()')


def compare_field(baseline,current,baseline_lock_failure=''):
    report=compare(baseline,current)
    confirmed=(baseline.get(LOCK_TEST)=='failure' and current.get(LOCK_TEST)=='passed'
               and all(token in baseline_lock_failure for token in LOCK_SIGNATURE))
    allowed={LOCK_TEST} if confirmed else set()
    unexpected_changes={key:values for key,values in report['changed_outcomes'].items() if key not in allowed}
    bad_baseline={key:state for key,state in baseline.items() if state!='passed' and key not in allowed}
    bad_current={key:state for key,state in current.items() if state!='passed'}
    report.update(
        confirmed_baseline_windows_lock_race=sorted(allowed),
        unexpected_outcome_changes=unexpected_changes,
        unexpected_baseline_failures=bad_baseline,
        candidate_failures_or_skips=bad_current,
        compatible=not(report['missing'] or unexpected_changes or bad_baseline or bad_current),
    )
    return report


def main():
    parser=argparse.ArgumentParser()
    for name in ('baseline','current','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    failure=''
    for case in ET.parse(args.baseline).iter('testcase'):
        if case.get('name')=='test_serialized_concurrent_writes':
            node=case.find('failure')
            if node is not None:failure=node.text or ''
    report=compare_field(read(args.baseline),read(args.current),failure)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['compatible'] else 1


if __name__=='__main__':raise SystemExit(main())
