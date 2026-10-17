"""Read the composed shell for historical source-contract assertions."""
def read_application_source(root):
    return '\n'.join((root / path).read_text(encoding='utf-8') for path in (
        'app/ui/main_window.py', 'app/ui/shell.py', 'app/ui/header.py', 'app/registry.py',
    ))


def assert_current_version_label(root):
    """Exercise the actual shell/version binding without creating operational data."""
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
    from shiboken6 import delete
    from app.registry import DEFAULT_MODULES
    from app.ui.main_window import APP_VERSION
    from app.ui.shell import build_shell
    app = QApplication.instance() or QApplication([])
    assert APP_VERSION == (root.parent / 'VERSION.txt').read_text().strip().removeprefix('v')
    shell = QMainWindow()
    shell.modules = DEFAULT_MODULES
    shell._raised_header_label = lambda text, name: QLabel(text)
    for name in ('toggle_theme', 'start_shift', 'close_shift', 'show_page', 'retry_pending'):
        setattr(shell, name, lambda *args: None)
    try:
        build_shell(shell, APP_VERSION)
        assert shell.version_label.text() == f'ΕΚΔΟΣΗ {APP_VERSION}'
        assert shell.version_label.objectName() == 'VersionLabel'
    finally:
        shell.close()
        delete(shell)
