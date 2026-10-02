# TDE Control Center

Private repository for the TDE Control Center Windows application.

## Current production version
- **Production release:** `v1.0.12`
- **Release EXE:** `TDE_CONTROL_CENTER_v1.0.12.exe`
- **Release source snapshot:** `TDE_CONTROL_CENTER_v1.0.12_SOURCE.zip`

The v1.0.12 release is the verified baseline for all future changes. It passed the full automated suite, UI stress/regression checks, Windows EXE startup smoke test and relocation smoke test.

## Frozen visual assets
`CURRENT_ASSETS/` preserves the exact approved:
- Hellenic Police emblem,
- Greece watermark.

These assets are part of the v1.0.12 visual identity and are not to be altered unless explicitly requested.

## Important
The existing `main/source/` tree is an older unpacked baseline and **is not the current production source**.

For any future maintenance or build, start from the v1.0.12 release source snapshot.

## Repository policy
To keep the repository simple and light:
- keep only the current production release in GitHub Releases,
- remove superseded release tags/branches and redundant build artifacts after verification,
- preserve the current EXE, source snapshot, SHA-256 and frozen visual assets.

## Maintenance rule
Before changing production:
1. map the affected subsystem,
2. use a test branch/copy,
3. run the checks,
4. make one visible production change at a time,
5. promote only after verification.
