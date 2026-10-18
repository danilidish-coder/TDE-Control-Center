# ΔΥΟ ΕΚΔΟΣΕΙΣ ΓΙΑ ΧΡΗΣΗ / ΔΟΚΙΜΗ — CONTROL CENTER
Ημερομηνία απογραφής: 18/10/2026. Αυτό είναι ΜΗΤΡΩΟ ΕΠΙΛΟΓΗΣ, όχι απόδειξη ότι η νέα έκδοση λειτουργεί απροβλημάτιστα στο πεδίο.

## 1. ΝΕΑ — προς επιτόπια δοκιμή (Phase 2, 17/10/2026)
- Ταυτότητα binary: `TDE_CONTROL_CENTER_PHASE2_CANDIDATE_2026-10-17.exe`.
- Πραγματικό SHA-256: `f782edc38cb7881a0e6862bc00aec49e111135c572789c02970d3877c77b6f02` — 65.176.381 bytes.
- Ακριβές source commit κατασκευής: `557558b5d25695ecf93c9e50be99f0c67afe7859`, branch `candidate/phase2-verified-20261017`.
- CI: https://github.com/danilidish-coder/TDE-Control-Center/actions/runs/39015354501 (228 PASS / 0 FAIL).
- Μόνιμο διαθέσιμο EXE στο Drive: https://drive.google.com/file/d/1gFt4hEAqUeAsgcw5HUCiZ2NNc2jDpFUp/view
- Διατηρημένο ZIP δοκιμών στο Drive: https://drive.google.com/file/d/1OHvPd2LakqskdegRDvkhy71UM45-qSth/view
- ΣΗΜΑΝΤΙΚΟ: Το GitHub Actions artifact έχει περιορισμένο χρόνο διατήρησης, δεν υπάρχει επιβεβαιωμένο μόνιμο GitHub Release για το Phase 2 EXE. Το source branch διατηρείται στο GitHub. Η πραγματική χρήση με Word/εκτυπώσεις/SMB παραμένει προς δοκιμή.

## 2. ΑΜΕΣΩΣ ΠΡΟΗΓΟΥΜΕΝΗ — v1.0.14
- Ακριβής γνωστή ταυτότητα EXE: `TDE_CONTROL_CENTER_v1.0.14.exe`, 59.828.619 bytes, SHA-256 `49bcc1a1214e0c0395a0e3f7fc96730b7d57e16642b27cdecfaec7f168f44573` (ιστορικός καταγεγραμμένος έλεγχος Drive).
- GitHub release: https://github.com/danilidish-coder/TDE-Control-Center/releases/tag/v1.0.14
- Γνωστό τελικό source commit παραγωγικού EXE: `a0076c9a1badab45b61be8fe845933c757ae424f`. Το GitHub tag `v1.0.14` δείχνει σε διαφορετικό, προγενέστερο commit, όπως τεκμηριώνεται στο `docs/VERSION_REGISTRY_EL.md`. Δεν πρέπει να εξισώνονται τα tags με τις ταυτότητες του binary.
- Αντίγραφο EXE στο Drive: ΕΚΚΡΕΜΕΙ επαναφόρτωση μετά την παλιά λανθασμένη εκκαθάριση· ο άδειος φάκελος δεν αποτελεί απόδειξη ότι το EXE υπάρχει.

## Κανόνας
Μόνο τα παραπάνω δύο binaries θεωρούνται υποψήφιες προς επιλογή εκδόσεις. Το παλαιότερο Git ιστορικό και τα releases δεν πιστοποιούν λειτουργικότητα και δεν διαγράφονται ως αποθήκη πηγαίου κώδικα. Δεν αντικαθίσταται η εγκατεστημένη έκδοση χωρίς νέα αποδοχή στο πεδίο.
