> **ΤΑΥΤΟΤΗΤΑ ΤΡΕΧΟΥΣΑΣ ΕΚΔΟΣΗΣ — ΕΛΕΓΧΟΣ 22/10/2026:** Πρώτα διαβάζεται αποκλειστικά το [ΕΝΕΡΓΟ ΜΗΤΡΩΟ ΕΠΙΛΟΓΗΣ](docs/ACTIVE_FIELD_VERSIONS_EL.md). Η έγκριση της 21/10 αφορά το EXE SHA-256 `f782edc38cb7881a0e6862bc00aec49e111135c572789c02970d3877c77b6f02` / source `557558b5d25695ecf93c9e50be99f0c67afe7859`, παρότι η UI σταθερά `APP_VERSION` εμφανίζει παλαιό «1.0.14». Η παλιότερη v1.0.14 με SHA `49bcc1a1214e0c0395a0e3f7fc96730b7d57e16642b27cdecfaec7f168f44573` είναι rollback. **Τα κατωτέρω ιστορικά στοιχεία είναι χρονολογικά και δεν υπερισχύουν του ενεργού μητρώου.** Δεν έχει αλλαχθεί ή ανακατασκευαστεί το EXE.

> **ΤΡΕΧΟΥΣΑ ΛΕΙΤΟΥΡΓΙΚΗ ΕΚΔΟΣΗ — ΕΓΚΡΙΣΗ ΧΡΗΣΤΗ 21/10/2026:** Το αρχείο `TDE_CONTROL_CENTER_v1.0.exe` (65.176.381 bytes, SHA-256 `f782edc38cb7881a0e6862bc00aec49e111135c572789c02970d3877c77b6f02`) είναι το τελευταίο εγκεκριμένο και λειτουργικό EXE. Ταυτίζεται κατά SHA-256 με το ήδη πιστοποιημένο Phase 2 Windows build της 17/10/2026, source `557558b5d25695ecf93c9e50be99f0c67afe7859`, Actions run 39015354501 (228 PASS), αρχειοθετημένο [στο Drive](https://drive.google.com/file/d/1G8xxadJ4ScBxlBYtPLhT97hiL7TU-BHi/view). Η ονομασία αρχείου δεν ταυτίζεται με τον εσωτερικό αριθμό έκδοσης. Η παλιότερη v1.0.14 διατηρείται ως ιστορική/rollback και ΔΕΝ είναι πλέον το πιο πρόσφατο εγκεκριμένο binary. Καμία αλλαγή κώδικα, tag ή εγκατάστασης προκύπτει από την παρούσα καταχώριση.

# Production status

> **Μητρώο ταυτότητας εκδόσεων:** [docs/VERSION_REGISTRY_EL.md](docs/VERSION_REGISTRY_EL.md). Για κάθε νέα έκδοση ενημερώνεται ταυτόχρονα αυτό το status, το μητρώο, το README και το μητρώο Drive. Το «validated production» είναι η καταγεγραμμένη έκδοση του έργου, όχι ανεξάρτητη επιβεβαίωση της έκδοσης εγκατάστασης σε κάθε υπηρεσιακό υπολογιστή.

> **Έλεγχος 16/10/2026:** Το EXE του Drive ελέγχθηκε από τα πραγματικά bytes: **59.828.619 bytes**, SHA-256 **49BCC1A1214E0C0395A0E3F7FC96730B7D57E16642B27CDECFAEC7F168F44573**, ακριβής συμφωνία με την παρούσα καταγραφή. Το tag `v1.0.14` δείχνει στο προγενέστερο commit `1a974727...`· το τελικό source commit που δηλώνεται εδώ είναι το επόμενο `a0076c9...`. Μην συγχέετε τις δύο πηγές.


## Historical validated production (before user approval 21/10/2026)
- Version: **v1.0.14**
- Authoritative source: `source/`
- Final source commit: `a0076c9a1badab45b61be8fe845933c757ae424f`
- Relevant regression validation: passed
- Windows EXE build: passed
- EXE startup smoke test: passed
- Release asset: `TDE_CONTROL_CENTER_v1.0.14.exe`
- EXE SHA-256: `49BCC1A1214E0C0395A0E3F7FC96730B7D57E16642B27CDECFAEC7F168F44573`

## Historical predecessor to v1.0.14
- Version: **v1.0.13**
- Retained as previous rollback release.
- SHA-256: `A967620FE8255E57AD402F6B40BD3B914AEF5D635C8B8D108BCAA7930F011413`

## Important binary note
PyInstaller rebuilds are not expected to be byte-for-byte identical across rebuilds. The listed SHA-256 identifies the final published v1.0.14 executable.

## Shared assets
Reusable approved visual files are stored separately in `SHARED_ASSETS/`.

## Repository retention
Keep the current validated source baseline and release, the previous validated rollback release, the shared visual assets, and only the workflows needed for maintenance.
