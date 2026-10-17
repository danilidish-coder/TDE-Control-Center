from pathlib import Path
import subprocess


def test_operational_data_and_credentials_are_ignored_without_ignoring_templates():
    root = Path(__file__).resolve().parents[2]
    paths = ['source/.tde_runtime/tde_control_center.sqlite3', 'source/.tde_runtime/archive/report.docx', 'source/TDE_DATA/tde.sqlite3', 'test.sqlite3-wal', 'test.sqlite3-shm', 'test.sqlite3-journal', '.env', '.env.local']
    result = subprocess.run(['git', 'check-ignore', '--no-index', '--', *paths], cwd=root, capture_output=True, text=True, check=True)
    assert set(result.stdout.splitlines()) == set(paths)
    result = subprocess.run(['git', 'check-ignore', '--no-index', '--', 'source/resources/Anafora_base.docx', '.env.example'], cwd=root, capture_output=True)
    assert result.returncode == 1
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=root, text=True).splitlines()
    assert not any('/.tde_runtime/' in p or '/TDE_DATA/' in p or p.endswith(('.sqlite3', '.sqlite3-wal', '.sqlite3-shm', '.sqlite3-journal')) or Path(p).name in ('.env', '.env.local') for p in tracked)
