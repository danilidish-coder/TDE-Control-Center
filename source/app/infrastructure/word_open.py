"""Open a private valid DOCX in Microsoft Word, independently of PDF preview."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
from zipfile import BadZipFile, ZipFile

from app.core.paths import preview_root, resolve_runtime_path


def find_word_executable() -> Path | None:
    candidates = []
    try:
        import winreg
    except ImportError:
        winreg = None
    if winreg is not None:
        key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\WINWORD.EXE'
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as handle:
                        value, _ = winreg.QueryValueEx(handle, '')
                        candidates.append(Path(os.path.expandvars(value.strip('"'))))
                except OSError:
                    continue
    executable = shutil.which('WINWORD.EXE')
    if executable:
        candidates.append(Path(executable))
    return next((p for p in candidates if p.name.upper() == 'WINWORD.EXE' and p.is_file()), None)


def open_word_document(path: str | Path) -> Path:
    source = resolve_runtime_path(path)
    if not source.is_file():
        raise FileNotFoundError(f'Δεν βρέθηκε το παραγόμενο DOCX: {source}')
    try:
        with ZipFile(source) as package:
            if source.suffix.lower() != '.docx' or package.testzip() is not None:
                raise BadZipFile('invalid DOCX package')
            package.read('word/document.xml')
            package.read('[Content_Types].xml')
    except (BadZipFile, KeyError) as exc:
        raise ValueError(f'Το αρχείο αναφοράς δεν είναι έγκυρο DOCX: {source}') from exc
    executable = find_word_executable()
    if executable is None:
        raise FileNotFoundError(
            f'Το DOCX δημιουργήθηκε και είναι έγκυρο: {source}\n'
            'Δεν εντοπίστηκε το Microsoft Word. Ελέγξτε την εγκατάστασή του. '
            'Η αναφορά παραμένει διαθέσιμη σε μορφή DOCX.'
        )
    snapshot = None
    try:
        folder = preview_root() / 'word_open'
        folder.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=f'{source.stem[:48]}_', suffix='.docx', dir=folder)
        os.close(fd)
        snapshot = Path(name)
        shutil.copyfile(source, snapshot)
        subprocess.Popen([str(executable), str(snapshot)])
    except OSError as exc:
        if snapshot is not None:
            snapshot.unlink(missing_ok=True)
        raise OSError(
            f'Το DOCX δημιουργήθηκε: {source}\n'
            f'Απέτυχε το άνοιγμα αντιγράφου στο Microsoft Word: {exc}'
        ) from exc
    return snapshot
