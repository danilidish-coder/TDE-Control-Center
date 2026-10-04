# GitHub structure

## Current baseline
- Functional version: **v1.0.13**
- Validated binary package: stored in Google Drive under `TDE-Control-Center/Releases/v1.0.13/`
- Verified v1.0.13 source: **not currently present in GitHub**

## Main branch
`main` contains only repository status/policy files and reusable shared assets.
The superseded v1.0.12 source tree has been removed.

## Shared assets
`SHARED_ASSETS/` contains standalone reusable visual files:
- approved Hellenic Police emblem,
- approved Greece map/watermark.

## Retention rule
After a new version is verified and explicitly accepted:
1. it becomes the single active baseline,
2. older Releases and their tags are deleted,
3. temporary/test/feature branches are deleted,
4. redundant Actions artifacts are deleted,
5. superseded source is removed from the active tree,
6. reusable shared assets are preserved separately.
