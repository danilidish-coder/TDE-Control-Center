# Production status

## Current validated production
- Version: **v1.0.13**
- Authoritative source: `source/`
- Source origin: reconstructed from the exact successful final-build inputs at commit `cfdb31cfa2b257f70db7db7b2bb0be93fd2e3f42`
- Targeted regression validation: passed
- Rebuilt EXE startup smoke test: passed
- Rebuilt EXE SHA-256: `A967620FE8255E57AD402F6B40BD3B914AEF5D635C8B8D108BCAA7930F011413`

## Important binary note
The rebuilt EXE is functionally validated but is not byte-for-byte identical to the earlier final executable. PyInstaller rebuilds are not expected to be binary-identical.

## Shared assets
Reusable approved visual files are stored separately in `SHARED_ASSETS/`.

## Repository retention
Keep one active validated source baseline, one current user-facing release, the shared visual assets, and only the workflows needed for maintenance.
