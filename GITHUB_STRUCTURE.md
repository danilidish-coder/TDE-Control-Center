# GitHub structure

## Current production
- Version: v1.0.1
- Frozen production branch: `production-v1.0.1`
- Release build branch: `release-v1.0.1`
- Downloadable release: GitHub Release `v1.0.1`
- Authoritative release source asset: `TDE_CONTROL_CENTER_v1.0.1_SOURCE.zip`

## Main branch
`main` is the navigation and maintenance branch. The existing `source/` directory is an older baseline and is explicitly marked as legacy until the verified v1.0.1 source is promoted there.

## Safety branches
- `backup-main-2026-10-02-pre-cleanup`: snapshot of main before repository cleanup.
- `production-v1.0.1`: frozen reference to the exact commit used by the current v1.0.1 release process.

## Rule for future versions
1. Work on a dedicated test/release branch.
2. Run automated and Windows build tests.
3. Publish the release with EXE and source snapshot.
4. Only after verification, synchronize the unpacked production source to `main/source`.
5. Keep previous versions in Releases and branches; do not overwrite history.
