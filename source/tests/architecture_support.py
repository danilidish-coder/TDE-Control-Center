"""Read the composed shell for historical source-contract assertions."""
def read_application_source(root):
    return '\n'.join((root / path).read_text(encoding='utf-8') for path in (
        'app/ui/main_window.py', 'app/ui/shell.py', 'app/ui/header.py', 'app/registry.py',
    ))
