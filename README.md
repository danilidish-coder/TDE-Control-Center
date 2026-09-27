# TDE Control Center

Private repository for the TDE Control Center Windows application.

## Repository layout
- `source/`: authoritative unpacked project source.
- `.github/workflows/build-windows.yml`: automated Windows EXE build and smoke test.
- `DEVELOPMENT_RULES.md`: permanent working rules for future maintenance.

## Working rule
GitHub `main` is the source of truth. Source files stay unpacked and directly editable. ZIP packages are created only when explicitly requested for transfer/download.
