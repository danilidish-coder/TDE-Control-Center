from pathlib import Path


def test_release_branding_and_build_files():
    root=Path(__file__).resolve().parents[1]
    main=(root/"app/ui/main_window.py").read_text(encoding="utf-8")
    assert "ΕΚΔΟΣΗ 1.0.12" in main
    assert "ΔΟΚΙΜΑΣΤΙΚΗ ΕΚΔΟΣΗ" not in main
    assert "NEW TEST" not in main
    assert (root/"TDE_CONTROL_CENTER_v1.0.spec").exists()
    assert "TDE_CONTROL_CENTER_v1.0" in (root/"TDE_CONTROL_CENTER_v1.0.spec").read_text(encoding="utf-8")
    assert "TDE_CONTROL_CENTER_v1.0.spec" in (root/"build_windows.bat").read_text(encoding="utf-8")
