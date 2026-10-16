# Production status

> **Μητρώο ταυτότητας εκδόσεων:** [docs/VERSION_REGISTRY_EL.md](docs/VERSION_REGISTRY_EL.md). Για κάθε νέα έκδοση ενημερώνεται ταυτόχρονα αυτό το status, το μητρώο, το README και το μητρώο Drive. Το «validated production» είναι η καταγεγραμμένη έκδοση του έργου, όχι ανεξάρτητη επιβεβαίωση της έκδοσης εγκατάστασης σε κάθε υπηρεσιακό υπολογιστή.

> **Έλεγχος 16/10/2026:** Το EXE του Drive ελέγχθηκε από τα πραγματικά bytes: **59.828.619 bytes**, SHA-256 **49BCC1A1214E0C0395A0E3F7FC96730B7D57E16642B27CDECFAEC7F168F44573**, ακριβής συμφωνία με την παρούσα καταγραφή. Το tag `v1.0.14` δείχνει στο προγενέστερο commit `1a974727...`· το τελικό source commit που δηλώνεται εδώ είναι το επόμενο `a0076c9...`. Μην συγχέετε τις δύο πηγές.


## Current validated production
- Version: **v1.0.14**
- Authoritative source: `source/`
- Final source commit: `a0076c9a1badab45b61be8fe845933c757ae424f`
- Relevant regression validation: passed
- Windows EXE build: passed
- EXE startup smoke test: passed
- Release asset: `TDE_CONTROL_CENTER_v1.0.14.exe`
- EXE SHA-256: `49BCC1A1214E0C0395A0E3F7FC96730B7D57E16642B27CDECFAEC7F168F44573`

## Previous validated production
- Version: **v1.0.13**
- Retained as previous rollback release.
- SHA-256: `A967620FE8255E57AD402F6B40BD3B914AEF5D635C8B8D108BCAA7930F011413`

## Important binary note
PyInstaller rebuilds are not expected to be byte-for-byte identical across rebuilds. The listed SHA-256 identifies the final published v1.0.14 executable.

## Shared assets
Reusable approved visual files are stored separately in `SHARED_ASSETS/`.

## Repository retention
Keep the current validated source baseline and release, the previous validated rollback release, the shared visual assets, and only the workflows needed for maintenance.
