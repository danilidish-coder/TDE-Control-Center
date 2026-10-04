# GitHub structure

## Current baseline
- Functional version: **v1.0.13**
- Authoritative source: `source/`
- Shared reusable visual assets: `SHARED_ASSETS/`

## Main branch
`main` is the single active production baseline.
The application source is stored directly and browsably under `source/`.

## Shared assets
`SHARED_ASSETS/` contains:
- approved Hellenic Police emblem,
- approved Greece map/watermark.

## Retention rule
After a new version is verified and explicitly accepted:
1. it becomes the single active baseline,
2. superseded Releases and tags are deleted,
3. temporary/test/feature branches are deleted,
4. redundant Actions artifacts are deleted,
5. the validated current source remains under `source/`,
6. reusable shared assets remain separate.
