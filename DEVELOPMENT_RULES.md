# Development Rules

## Functional baseline
- An explicitly accepted functional version becomes the single active baseline.
- Do not keep superseded application versions in the active repository tree or Releases.
- Do not relabel older source as the current version.
- If the verified current source is unavailable, state that clearly and do not build from an older source.

## Change workflow
- Read and verify the current baseline before any code change.
- Experimental work may use a temporary feature/test branch.
- Once a new version is explicitly accepted as functional, clean obsolete releases, tags, temporary branches and redundant build artifacts.
- Keep only the source and deliverables that actually belong to the accepted version.

## Shared assets
- Reusable visual assets must remain separate from application source in `SHARED_ASSETS/`.
- The shared police emblem and Greece map/watermark must not be redrawn, recolored or replaced unless explicitly requested.
- Shared assets may be copied/referenced for future projects only when explicitly required.

## Deliverables
- Stable Releases should expose only the current user-facing Windows EXE unless another artifact is explicitly requested.
- ZIP transfer packages are created only when explicitly requested.
- Test EXEs belong to temporary Actions artifacts, not to the permanent release folder.

## Current Control Center status
- Validated functional version: **v1.0.13**
- Verified v1.0.13 source is not currently available in GitHub.
- Do not use the former v1.0.12 source as a substitute.
