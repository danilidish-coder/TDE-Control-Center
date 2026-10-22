from pathlib import Path
from app.version import APP_VERSION,WINDOWS_VERSION,EXE_NAME
from app.ui.main_window import APP_VERSION as GUI_VERSION


def test_candidate_version_single_identity_and_native_windows_resource_spec():
    repo=Path(__file__).resolve().parents[2]
    assert (repo/'VERSION.txt').read_text().strip()==f'v{APP_VERSION}'
    assert GUI_VERSION==APP_VERSION=='1.0.15'
    assert '.'.join(map(str,WINDOWS_VERSION[:3]))==APP_VERSION
    assert EXE_NAME==f'TDE_CONTROL_CENTER_v{APP_VERSION}_CANDIDATE'
    spec=(repo/'source/TDE_CONTROL_CENTER_v1.0.spec').read_text()
    assert "runpy.run_path(str(root / 'app' / 'version.py'))" in spec
    assert "name=identity['EXE_NAME']" in spec and 'version=version_info' in spec
