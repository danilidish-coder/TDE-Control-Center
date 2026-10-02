# TDE Control Center

Private repository for the TDE Control Center Windows application.

## Current production version
- **Production release:** `v1.0.1`
- **Published:** 2026-10-01
- **Release EXE:** `TDE_CONTROL_CENTER_v1.0.1.exe`
- **Release source snapshot:** `TDE_CONTROL_CENTER_v1.0.1_SOURCE.zip`
- **Release build branch:** `release-v1.0.1`

The v1.0.1 EXE was built by the verified GitHub Actions release workflow from the baseline source plus the v0.5/v0.6/v1.0/v1.0.1 overlays and transforms.

## Important
The existing `main/source/` tree is an older unpacked baseline and **must not be treated as the current production source** until it is replaced by the verified v1.0.1 source snapshot.

For questions about the application currently in production, use the v1.0.1 release source as the reference.

## Repository layout
- `source/` — legacy unpacked baseline; retained for history until production-source promotion is completed.
- `release-v1.0.1` — deterministic build inputs used for the current production release.
- `unified_v05/`, `unified_v06/`, `release_v10/`, `release_v101/` — overlays/transforms used to assemble v1.0.1.
- `.github/workflows/build-release-v10.yml` — Windows build, automated tests, smoke tests and release packaging.
- `DEVELOPMENT_RULES.md` — maintenance rules.
- GitHub **Releases** — authoritative downloadable EXE/source bundles.

## Maintenance rule
Before changing production:
1. map the affected subsystem,
2. keep a backup,
3. work on a test copy/branch,
4. verify with tests,
5. make one visible production change at a time.

Do not build a production EXE from `main/source/` until that tree is explicitly synchronized with the current production release.
