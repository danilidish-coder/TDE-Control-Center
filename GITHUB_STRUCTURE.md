# GitHub structure

## Current production
- Version: **v1.0.12**
- Downloadable release: GitHub Release `v1.0.12`
- Authoritative EXE: `TDE_CONTROL_CENTER_v1.0.12.exe`
- Authoritative source: `TDE_CONTROL_CENTER_v1.0.12_SOURCE.zip`

## Main branch
`main` is the navigation and maintenance branch.

The existing `source/` directory is legacy. The v1.0.12 release source snapshot is the production source of truth.

## Current visual assets
`CURRENT_ASSETS/` contains the exact approved police emblem and Greece watermark from v1.0.12.

## Retention rule
After a new version is verified and explicitly accepted:
1. it becomes the single production baseline,
2. keep its EXE, source snapshot and SHA-256,
3. keep its approved frozen visual assets,
4. remove superseded releases, tags and temporary release branches,
5. remove redundant GitHub Actions artifacts.

This replaces the older policy of keeping every release visible.
