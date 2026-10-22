> **ΤΑΥΤΟΤΗΤΑ ΤΡΕΧΟΥΣΑΣ ΕΚΔΟΣΗΣ — ΕΛΕΓΧΟΣ 22/10/2026:** Πρώτα διαβάζεται αποκλειστικά το [ΕΝΕΡΓΟ ΜΗΤΡΩΟ ΕΠΙΛΟΓΗΣ](ACTIVE_FIELD_VERSIONS_EL.md). Η έγκριση της 21/10 αφορά το EXE SHA-256 `f782edc38cb7881a0e6862bc00aec49e111135c572789c02970d3877c77b6f02` / source `557558b5d25695ecf93c9e50be99f0c67afe7859`, παρότι η UI σταθερά `APP_VERSION` εμφανίζει παλαιό «1.0.14». Η παλιότερη v1.0.14 με SHA `49bcc1a1214e0c0395a0e3f7fc96730b7d57e16642b27cdecfaec7f168f44573` είναι rollback. **Τα κατωτέρω ιστορικά στοιχεία είναι χρονολογικά και δεν υπερισχύουν του ενεργού μητρώου.** Δεν έχει αλλαχθεί ή ανακατασκευαστεί το EXE.

> **ΤΡΕΧΟΥΣΑ ΛΕΙΤΟΥΡΓΙΚΗ ΕΚΔΟΣΗ — ΕΓΚΡΙΣΗ ΧΡΗΣΤΗ 21/10/2026:** Το αρχείο `TDE_CONTROL_CENTER_v1.0.exe` (65.176.381 bytes, SHA-256 `f782edc38cb7881a0e6862bc00aec49e111135c572789c02970d3877c77b6f02`) είναι το τελευταίο εγκεκριμένο και λειτουργικό EXE. Ταυτίζεται κατά SHA-256 με το ήδη πιστοποιημένο Phase 2 Windows build της 17/10/2026, source `557558b5d25695ecf93c9e50be99f0c67afe7859`, Actions run 39015354501 (228 PASS), αρχειοθετημένο [στο Drive](https://drive.google.com/file/d/1G8xxadJ4ScBxlBYtPLhT97hiL7TU-BHi/view). Η ονομασία αρχείου δεν ταυτίζεται με τον εσωτερικό αριθμό έκδοσης. Η παλιότερη v1.0.14 διατηρείται ως ιστορική/rollback και ΔΕΝ είναι πλέον το πιο πρόσφατο εγκεκριμένο binary. Καμία αλλαγή κώδικα, tag ή εγκατάστασης προκύπτει από την παρούσα καταχώριση.

# ΜΗΤΡΩΟ ΕΚΔΟΣΕΩΝ — CONTROL CENTER

**Ιστορική βάση απογραφής: 16/10/2026.** Αυτό είναι αρχείο τεκμηρίωσης της προέλευσης παλαιών εκδόσεων. Η τρέχουσα εγκεκριμένη έκδοση δηλώνεται ΜΟΝΟ στο ενεργό `docs/ACTIVE_FIELD_VERSIONS_EL.md`. Η πληροφορία για την κατάσταση χρήσης προέρχεται από το `PRODUCTION_STATUS.md` και χρειάζεται επιβεβαίωση για το ποιο EXE είναι εγκατεστημένο σε κάθε φυσικό σταθμό.

## Κανόνας ταυτοποίησης

Καμία έκδοση δεν αναγνωρίζεται από το όνομα EXE, το branch `main`, την εικόνα στην οθόνη ή τον αριθμό έκδοσης μόνο. **Υποχρεωτική τετράδα**: (1) πλήρες Git source commit SHA, (2) συγκεκριμένο build/Actions run και αποτέλεσμα δοκιμών, (3) SHA-256 των πραγματικών bytes του EXE και μέγεθος, (4) σύνδεσμος στο ακριβές αρχειοθετημένο binary ή release asset. Το όνομα της έκδοσης είναι πρόσθετη ετικέτα, όχι απόδειξη. Αν λείπει στοιχείο, σημειώνεται ΕΚΚΡΕΜΗΣ ΕΠΑΛΗΘΕΥΣΗ, ποτέ εικαζόμενη αντιστοίχιση.

## Ιστορική έκδοση v1.0.14 — επικυρωμένη πριν από 21/10/2026 (rollback)

- **Πηγαίος κώδικας τελικού build, όπως καταγράφεται στο GitHub:** `a0076c9a1badab45b61be8fe845933c757ae424f` ([source commit](https://github.com/danilidish-coder/TDE-Control-Center/commit/a0076c9a1badab45b61be8fe845933c757ae424f)).
- **EXE:** `TDE_CONTROL_CENTER_v1.0.14.exe`, **59.828.619 bytes**.
- **SHA-256 πραγματικού αρχείου Google Drive, επανυπολογισμένο στις 16/10/2026:** `49bcc1a1214e0c0395a0e3f7fc96730b7d57e16642b27cdecfaec7f168f44573`.
- **Αρχείο Drive:** [επαληθευμένο binary](https://drive.google.com/file/d/1UXzwWNtAY27NtEiaGnAqN6dqW0gz6lT_/view) · [φάκελος](https://drive.google.com/drive/folders/1JNJqQR_vL0BowSu5wvNcqMu0567w9XO5).
- **Διασταύρωση:** το hash του binary συμφωνεί **ακριβώς** με το `PRODUCTION_STATUS.md` του main, το οποίο αναφέρει επιτυχή Windows EXE build, smoke και σχετικό regression. Δεν επανεκτελέστηκαν αυτά τα tests κατά τη σύνταξη του μητρώου· δεν ελέγχθηκαν τα bytes του GitHub release asset.
- **Πηγαίος κώδικας στο main πριν τη σημερινή ενημέρωση τεκμηρίωσης:** `cade2e152c1044a2d9ce8050eef299ed4536c58b`. Σύγκριση με το `a0076c9...`: **μόνο** το `PRODUCTION_STATUS.md` αλλάζει, όχι ο κώδικας εφαρμογής.
- **ΠΡΟΣΟΧΗ — το tag `v1.0.14` ΔΕΝ είναι το τελικό source commit.** Δείχνει στο `1a974727063b64d4c29b41f83df89d31da87d7ca`. Ακολούθησε η αλλαγή στα Περιοδικά `a0076c9...`. Μην θεωρήσεις ποτέ αυτό το tag πλήρες τελικό build-source. Δεν μετακινήθηκε το ιστορικό tag.

**Επαλήθευση παραγωγικού σταθμού:** η κατάσταση στο GitHub χαρακτηρίζει τη v1.0.14 validated production, αλλά δεν έχει ελεγχθεί το SHA του EXE που είναι εγκατεστημένο σε κάθε πραγματικό υπηρεσιακό υπολογιστή. Για κάθε σταθμό χρειάζεται SHA-256 του εγκατεστημένου EXE και αντιστοίχιση με την παραπάνω ταυτότητα.

## Προηγούμενη έκδοση v1.0.13 — ιστορικό / επαναφορά

- Git tag `v1.0.13` → `d58d5c00622c2f4b67bc85b635d8e6470a46cea9`.
- Το `PRODUCTION_STATUS.md` δηλώνει επαληθευμένο **rebuild** SHA-256 `A967620FE8255E57AD402F6B40BD3B914AEF5D635C8B8D108BCAA7930F011413`.
- Το ιστορικό `README.md` περιέγραφε άλλο, **αρχικό παραδομένο EXE** `TDE_CONTROL_CENTER_v1.0.13_FINAL.exe` με SHA-256 `1DEB923EAB1060B59BB7DA9380B0CD463B17EA0A8B7F3C90BC1CD0E9BEE59DD6`.
- Αυτά είναι **δύο διαφορετικά binaries**. Δεν έγινε επανυπολογισμός των bytes τους στην απογραφή 16/10. Καμία αυτοματοποιημένη εξίσωση των δύο· κάθε rollback απαιτεί ακριβές binary/hash και επιβεβαίωση.

## Άλλες ιστορικές γραμμές — ΟΧΙ τρέχουσα παραγωγή

| Αναφορά | SHA commit κατά τον έλεγχο 16/10/2026 | Χαρακτηρισμός |
| --- | --- | --- |
| `backup/v1.0.14-not-in-use` | `f7293042bc4dcd36516be0f21875344d7f6f5d91` | Παλαιότερη εφεδρική/μη επιλεγμένη υλοποίηση· τα παλιά STATUS εκεί αναφέρονται σε παλαιότερο χρόνο |
| `archive/drive-v1014-20261012` | `f92630e82793b6c52a05698d63f11c97d74f0c86` | Αρχειοθέτηση/παράδοση, όχι παραγωγικός κορμός |
| `temp-release-handoff-20261004` | `c96920e30be7d3a9a2898fad846b79be06aed064` | Ιστορικό handoff |
| `test-fines-word-preview` | `4ef61ba08d0de1d216ce8ba1219d9d37f2779c72` | Ιστορικό δοκιμών |
| `refactor/modular-phase1` | `8ddf040d7a586bb6e8d464b6e7944a01b0a5b85c` κατά τη στιγμή ελέγχου | **Ενεργή, μεταβαλλόμενη** modular εργασία· όχι παραγωγική έκδοση |

## Υποχρεωτική διαδικασία για τις επόμενες αλλαγές

1. Πριν από εργασία ελέγχονται αυτό το μητρώο, το `PRODUCTION_STATUS.md`, το ακριβές source commit και το πραγματικό παραγωγικό EXE. Δεν γίνεται ανάπτυξη από branch μόνο λόγω ονόματος.
2. Η αλλαγή γίνεται σε ξεχωριστό development branch, με διατηρημένη την προηγούμενη έκδοση, δοκιμαστικά δεδομένα και σαφή σύγκριση συμπεριφοράς.
3. Πριν παραδοθεί νέα έκδοση: ακριβές source SHA, επιτυχείς απαιτούμενες δοκιμές Windows, build run ID/URL, EXE SHA-256 και μέγεθος, ίδιο binary σε GitHub/Drive επαληθευμένο με hash, λίστα μεταβολών και δυνατότητα rollback.
4. Χωρίς πλήρη ταυτοποίηση: **δεν** αλλάζει το παραγωγικό EXE, το main ή το status «τρέχουσα».
5. Προηγούμενα release tags, branches, EXE και ιστορικό δεν διαγράφονται ούτε μετακινούνται αυτόματα. Δεν εκτελούνται παλιά cleanup/publish workflows χωρίς έλεγχο του περιεχομένου τους: μερικά έχουν παλαιότερους σταθερούς αριθμούς εκδόσεων ή εντολές διαγραφής.
6. Μόνο μετά από ρητή έγκριση παραλαβής ενημερώνονται **στην ίδια παράδοση** το παρόν αρχείο, το `PRODUCTION_STATUS.md`, το `README.md` και το υπάρχον Μητρώο CONTROL CENTER στο Google Drive. Ο χρήστης δεν συντηρεί αυτές τις αντιστοιχίσεις χειροκίνητα.

## Πηγές

- [PRODUCTION_STATUS.md](../PRODUCTION_STATUS.md)
- [Μητρώο CONTROL CENTER στο Google Drive](https://docs.google.com/document/d/1QeYfHiBOztYqBJHjRQMHotDKOxn0TnkDiEMs1MZZkJM/edit)
- [Modular phase 1 (εργασία, όχι έκδοση)](https://github.com/danilidish-coder/TDE-Control-Center/blob/refactor/modular-phase1/docs/MODULAR_PHASE1.md)

## Έλεγχος παρωχημένων GitHub Actions — 16/10/2026

Τα παλιά workflows `cleanup-releases.yml`, `publish-release.yml`, `prepare-current-delivery.yml` και `package-v1013-full.yml` **απενεργοποιήθηκαν στο main** (manual-only με job `if: false`). Το παλιό cleanup μπορούσε να διαγράψει releases, tags, branches και artifacts, ενώ τα άλλα χρησιμοποιούσαν παλιές σταθερές εκδόσεις ή `--clobber` σε υπάρχοντα release assets. Δεν εκτελέστηκε cleanup ή publication. Τα παλιά script σώζονται στο ιστορικό Git. Όταν ζητηθεί νέα δημοσίευση, χρειάζεται **καινούργιο ασφαλές workflow** με ρητό source SHA, πλήρες EXE digest, μη αντικατάσταση παλιάς έκδοσης, δοκιμές και έγκριση. Άλλα ιστορικά branches ενδέχεται να κρατούν παλιά workflows· δεν γίνονται pushes σε αυτά χωρίς ανεξάρτητο έλεγχο.

**Σημείωση:** οι αλλαγές τεκμηρίωσης και workflows στο main δεν μεταβάλλουν κανένα αρχείο στο `source/`. Το `a0076c9...` παραμένει το δηλωμένο τελικό source commit της v1.0.14, ενώ το HEAD του main μπορεί πλέον να είναι νεότερο επειδή έγιναν ασφαλιστικές ενημερώσεις αρχείων συντήρησης.

## Νέα αρχειοθετημένη υποψήφια Φάσης 2 — 17/10/2026

**ΚΑΤΑΣΤΑΣΗ: ολοκληρωμένη τεχνική πιστοποίηση· ΟΧΙ ακόμη εγκεκριμένη για παραγωγική εγκατάσταση.** Η ήδη εγκατεστημένη/καταγεγραμμένη λειτουργική v1.0.14 και όλα τα παλιότερα releases, tags, branches και binaries **δεν διαγράφηκαν, μετακινήθηκαν ή αντικαταστάθηκαν**.

- Source κατασκευής ακριβούς EXE: `557558b5d25695ecf93c9e50be99f0c67afe7859` — [σταθερό GitHub branch υποψήφιας](https://github.com/danilidish-coder/TDE-Control-Center/tree/candidate/phase2-verified-20261017).
- Source/εργαλεία τελικής πιστοποίησης: `70c1eb0ddf8b3bfcbabbb4e58afc1ca2c3097909`. Ασφαλές τελικό checkpoint αναφοράς: `e9d9ff221171ccb1bba4c714947ce63b4755b837` στο [audit branch](https://github.com/danilidish-coder/TDE-Control-Center/tree/audit/phase2-hardening-20261017).
- Windows Actions [39015354501 — SUCCESS](https://github.com/danilidish-coder/TDE-Control-Center/actions/runs/39015354501): 228 PASS/0 FAIL σε Windows και Linux· native frozen EXE, συνθετικό πρόστιμο, 6 ενότητες, DOCX/Excel, SQLite/backup, όρια χρόνων. **Δεν υποκαθιστά πραγματικό εγκατεστημένο Office/SMB/εκτύπωση.**
- Ακριβές EXE: `TDE_CONTROL_CENTER_PHASE2_CANDIDATE_2026-10-17.exe`, **65.176.381 bytes**, SHA-256 **`f782edc38cb7881a0e6862bc00aec49e111135c572789c02970d3877c77b6f02`**. Το SHA επανυπολογίστηκε από τοπική εξαγωγή του επιτυχούς Actions artifact και ξανά από το **κατεβασμένο αρχείο μετά τη μεταφόρτωσή του στο Drive**: απόλυτη συμφωνία. Το όνομα αρχείου είναι ταυτότητα παράδοσης, όχι νέα ενσωματωμένη έκδοση (το GUI εξακολουθεί να αναφέρει 1.0.14).
- **Μόνιμο αρχείο στο Google Drive:** [ακριβές EXE](https://drive.google.com/file/d/1G8xxadJ4ScBxlBYtPLhT97hiL7TU-BHi/view) · [νέος ξεχωριστός φάκελος](https://drive.google.com/drive/folders/1Zg8kyDURdrr1UeNjRkdVXjFfZfMhhuSj). Ο φάκελος `v1.0.14` παραμένει ανέπαφος.
- **GitHub binary:** το αρχικό επιτυχές [Actions artifact](https://github.com/danilidish-coder/TDE-Control-Center/actions/runs/39015354501/artifacts/12094855467) έχει διατήρηση 14 ημερών, **δεν** αποτελεί μόνιμο release. Προσπάθεια δημιουργίας ξεχωριστού μη παραγωγικού prerelease στο run [39016434739](https://github.com/danilidish-coder/TDE-Control-Center/actions/runs/39016434739) μπλοκαρίστηκε με **HTTP 403 Resource not accessible by integration**. Προσπάθεια δημιουργίας git tag μέσω Actions στο [39016662672](https://github.com/danilidish-coder/TDE-Control-Center/actions/runs/39016662672) αποκλείστηκε λόγω έλλειψης `workflows` permission της GitHub εφαρμογής. **Δεν** δημιουργήθηκε νέο Release ή tag. Δεν απαιτείται νέα κατασκευή EXE για αυτά τα ζητήματα δικαιωμάτων. Μέχρι να επιτραπεί έκδοση release με κατάλληλο εξουσιοδοτημένο λογαριασμό, η μόνιμη θέση του EXE είναι το παραπάνω Google Drive και στο GitHub υπάρχει ακριβές source branch, μητρώο SHA και προσωρινό Actions artifact.
- Επιτόπια εκκρεμότητα: πραγματικό άνοιγμα/εκτύπωση με Word/Excel και υπηρεσιακή κοινόχρηστη SMB λειτουργία/ACL, με synthetic στοιχεία. Τα αίτια του αναφερθέντος πραγματικού περιστατικού Word παραμένουν μη αποδειγμένα.

**ΚΑΝΟΝΑΣ:** καμία διαγραφή παλιάς έκδοσης χωρίς νέα ρητή εντολή του χρήστη. Καμία αυτόματη μετάβαση production/main, αλλαγή v1.0.14 ή κατάργηση δυνατότητας rollback.
