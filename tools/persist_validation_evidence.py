"""CI-only evidence ref for environments that can read Git but not the Actions API."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

REF = 'refs/heads/validation/control-center-modular-phase1'


def git(*args, environment=None):
    return subprocess.check_output(['git', *args], env=environment, text=True, encoding='utf-8').strip()


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('Evidence publication is restricted to this GitHub Actions job')
    validation = Path('validation')
    validation.mkdir(exist_ok=True)
    metadata = {
        'source_commit': os.environ['GITHUB_SHA'],
        'job_status': os.environ['VALIDATION_JOB_STATUS'],
        'run_url': f"{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}",
        'production_release': False,
    }
    (validation / 'run.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    previous = git('ls-remote', 'origin', REF)
    parent = []
    if previous:
        sha = previous.split()[0]
        git('fetch', '--no-tags', 'origin', REF)
        parent = ['-p', sha]
    with tempfile.TemporaryDirectory(prefix='tde-evidence-index-') as scratch:
        environment = dict(os.environ, GIT_INDEX_FILE=str(Path(scratch) / 'index'))
        git('read-tree', '--empty', environment=environment)
        paths = sorted(str(p) for p in validation.rglob('*') if p.is_file() and p.suffix in ('.json', '.xml', '.log'))
        git('add', '--', *paths, environment=environment)
        tree = git('write-tree', environment=environment)
        commit = git('-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com', 'commit-tree', tree, *parent, '-m', f"Phase 1 validation for {metadata['source_commit']}", environment=environment)
        git('push', 'origin', f'{commit}:{REF}')
    print(f'Evidence saved to {REF} for {metadata["source_commit"]}')


if __name__ == '__main__': main()
