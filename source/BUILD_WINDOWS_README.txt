TDE CONTROL CENTER - RELEASE v1.0 WINDOWS BUILD SOURCE

Build on Windows x64:
  build_windows.bat

Required build packages:
  python -m pip install -r requirements-build.txt

Output:
  dist\TDE_CONTROL_CENTER_v1.0.exe

The application does not require Python on the service workstation once built.
Keep the existing .tde_runtime folder beside the EXE when upgrading or moving
the application so the database and archived Word/Excel files continue intact.
