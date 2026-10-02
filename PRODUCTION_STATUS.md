# Production status

## Current production
- Version: **v1.0.12**
- Release commit: `0da71d9ad5e8aa3b8d5a3f553e8d0abd42dc8d3a`
- Release EXE: `TDE_CONTROL_CENTER_v1.0.12.exe`
- EXE SHA-256: `4a2355580479f063f67b867241e8babb9e4314d5875a2dfed6bbb0689483202d`
- Source snapshot: `TDE_CONTROL_CENTER_v1.0.12_SOURCE.zip`
- Successful Windows build/test run: `37070025655`

## Source of truth
For all future work, **v1.0.12 is the only production baseline**.

The authoritative recoverable source is the GitHub Release asset:
`TDE_CONTROL_CENTER_v1.0.12_SOURCE.zip`.

The old `main/source/` tree is legacy and must not be used as production source.

## Frozen visual assets
The exact approved visual assets are preserved in `CURRENT_ASSETS/`:
- user-selected Hellenic Police emblem,
- Greece watermark used in v1.0.12.

Do not redraw, recolor or replace them unless explicitly requested.

## Repository retention
Only the current production release is retained in GitHub Releases. Older release downloads, tags, release branches and redundant Actions artifacts are removed after the current release is confirmed.
