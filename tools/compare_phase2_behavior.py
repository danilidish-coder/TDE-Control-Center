"""Compare every snapshot value, allowing only the required active VAS annotation."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

PREVIEW = 'preview/ΒΑΣ_ΒΑΡΔΙΑ_1.docx'
PART = 'word/document.xml'
ANNOTATION = '\nΠΡΟΕΠΙΣΚΟΠΗΣΗ — ΕΝΕΡΓΗ ΒΑΡΔΙΑ (προσωρινή λήξη).'


def compare_behavior(baseline, current):
    normalized = deepcopy(current)
    candidates = [name for name in (PREVIEW, PREVIEW.replace('/', chr(92)))
                  if name in baseline.get('documents', {}) and name in normalized.get('documents', {})]
    preview = candidates[0] if len(candidates) == 1 else PREVIEW
    xml = normalized.get('documents', {}).get(preview, {}).get(PART, '')
    annotation_present = len(candidates) == 1 and xml.count(ANNOTATION) == 1
    if annotation_present:
        normalized['documents'][preview][PART] = xml.replace(ANNOTATION, '', 1)
    return {
        'compatible': annotation_present and baseline == normalized,
        'active_preview_annotation_present_once': annotation_present,
        'authorized_change': PREVIEW + '/' + PART,
        'all_other_values_equal': baseline == normalized,
        'closed_reports_require_exact_equality': True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--current', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = compare_behavior(json.loads(args.baseline.read_text(encoding='utf-8')), json.loads(args.current.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['compatible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
