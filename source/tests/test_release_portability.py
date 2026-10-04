from pathlib import Path

import app.core.paths as paths


def test_resolve_runtime_path_rebases_old_runtime(monkeypatch, tmp_path: Path):
    current = tmp_path / ".tde_runtime"
    target = current / "archive" / "ΑΡΝΗΣΕΙΣ" / "2026" / "09" / "test.docx"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")

    monkeypatch.setattr(paths, "runtime_root", lambda: current)
    old = Path("Z:/OLD_LOCATION/.tde_runtime/archive/ΑΡΝΗΣΕΙΣ/2026/09/test.docx")

    assert paths.resolve_runtime_path(old) == target


def test_resolve_runtime_path_keeps_existing_external_path(monkeypatch, tmp_path: Path):
    current = tmp_path / ".tde_runtime"
    current.mkdir()
    external = tmp_path / "external.docx"
    external.write_bytes(b"x")

    monkeypatch.setattr(paths, "runtime_root", lambda: current)
    assert paths.resolve_runtime_path(external) == external
