# Development Rules

## Functional baseline
- The explicitly accepted functional version is the single active baseline.
- Current baseline: **v1.0.13**.
- Authoritative source is stored directly under `source/`.
- Do not relabel older source as the current version.

## Change workflow
- Read and verify the current `source/` baseline before any code change.
- Experimental work may use a temporary feature/test branch.
- Promote only after tests and required smoke checks pass.
- After promotion, remove obsolete releases, tags, temporary branches and redundant artifacts.

## Shared assets
- Reusable visual assets remain separate under `SHARED_ASSETS/`.
- The police emblem and Greece map/watermark must not be redrawn, recolored or replaced unless explicitly requested.

## Deliverables
- GitHub keeps the validated source, history, tests, maintenance workflows and version references.
- Stable Releases expose the current user-facing Windows EXE.
- ZIP transfer packages are created only when explicitly requested.

## Validation
- Run the relevant automated tests before promotion.
- Windows EXE builds must pass a startup smoke test before being treated as ready.
