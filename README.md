# TDE Control Center

Private repository for the TDE Control Center Windows application.

## Current validated version
- **Validated functional version:** `v1.0.13`
- **Validated source:** `source/`
- The source was reconstructed from the exact inputs of the successful final v1.0.13 build and passed the same targeted regression tests.
- A rebuilt Windows EXE from this source also passed the startup smoke test.

## Shared visual assets
`SHARED_ASSETS/` contains the approved reusable:
- Hellenic Police emblem,
- Greece map/watermark.

These files are standalone assets and are not owned by a specific application version.

## Retention rule
When a version is explicitly accepted as functional:
1. it becomes the single active baseline,
2. superseded releases, tags, temporary branches and redundant artifacts are removed,
3. the validated source remains directly browsable in `source/`,
4. reusable shared assets remain separately available.
