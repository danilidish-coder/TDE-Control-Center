from __future__ import annotations
import re
import shutil
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from app.core.textnorm import normalize_text

GREEK_MONTHS={1:"ΙΑΝΟΥΑΡΙΟΣ",2:"ΦΕΒΡΟΥΑΡΙΟΣ",3:"ΜΑΡΤΙΟΣ",4:"ΑΠΡΙΛΙΟΣ",5:"ΜΑΙΟΣ",6:"ΙΟΥΝΙΟΣ",7:"ΙΟΥΛΙΟΣ",8:"ΑΥΓΟΥΣΤΟΣ",9:"ΣΕΠΤΕΜΒΡΙΟΣ",10:"ΟΚΤΩΒΡΙΟΣ",11:"ΝΟΕΜΒΡΙΟΣ",12:"ΔΕΚΕΜΒΡΙΟΣ"}

@dataclass(frozen=True)
class DateToken:
    start:int
    end:int
    value:date
    order:str
    separator:str
    year_digits:int
    def render(self,value:date)->str:
        year=f"{value.year:04d}" if self.year_digits==4 else f"{value.year%100:02d}"
        parts={"D":f"{value.day:02d}","M":f"{value.month:02d}","Y":year}
        return self.separator.join(parts[ch] for ch in self.order)

_DATE_PATTERNS=(
 ("YMD",re.compile(r"(?<!\d)(?P<y>20\d{2})(?P<s>[-_.])(?P<m>0[1-9]|1[0-2])(?P=s)(?P<d>0[1-9]|[12]\d|3[01])(?!\d)"),4),
 ("DMY",re.compile(r"(?<!\d)(?P<d>0[1-9]|[12]\d|3[01])(?P<s>[-_.])(?P<m>0[1-9]|1[0-2])(?P=s)(?P<y>20\d{2})(?!\d)"),4),
 ("DMY",re.compile(r"(?<!\d)(?P<d>0[1-9]|[12]\d|3[01])(?P<s>[-_.])(?P<m>0[1-9]|1[0-2])(?P=s)(?P<y>\d{2})(?!\d)"),2),
)

def _full_year(raw:str)->int:
    return int(raw) if len(raw)==4 else 2000+int(raw)

def date_tokens(filename:str)->list[DateToken]:
    found=[]; occupied=[]
    for order,pattern,year_digits in _DATE_PATTERNS:
        for match in pattern.finditer(filename):
            span=match.span()
            if any(not(span[1]<=a or span[0]>=b) for a,b in occupied):
                continue
            try:
                value=date(_full_year(match.group("y")),int(match.group("m")),int(match.group("d")))
            except ValueError:
                continue
            found.append(DateToken(span[0],span[1],value,order,match.group("s"),year_digits))
            occupied.append(span)
    return sorted(found,key=lambda token:token.start)

def filename_date(filename:str)->tuple[date,DateToken]:
    tokens=date_tokens(filename)
    if not tokens:
        raise ValueError(f"Δεν βρέθηκε έγκυρη ημερομηνία στο όνομα: {filename}")
    if len({token.value for token in tokens})>1:
        raise ValueError(f"Περισσότερες από μία διαφορετικές ημερομηνίες στο όνομα: {filename}")
    return tokens[0].value,tokens[0]

def replace_filename_date(filename:str,target:date)->str:
    current,_=filename_date(filename)
    tokens=[token for token in date_tokens(filename) if token.value==current]
    result=filename
    for token in reversed(tokens):
        result=result[:token.start]+token.render(target)+result[token.end:]
    return result

def month_folder_name(value:date)->str:
    return f"{value.month}. {GREEK_MONTHS[value.month]} {value.year:04d}"

def destination_folder(archive_root:str|Path,value:date)->Path:
    return Path(archive_root)/f"{value.year:04d}"/month_folder_name(value)

def move_orphan_into_archive(source_file:str|Path,archive_root:str|Path|None=None)->Path:
    source=Path(source_file)
    if not source.is_file():
        raise FileNotFoundError(source)
    value,_=filename_date(source.name)
    root=Path(archive_root) if archive_root is not None else source.parent
    target_dir=destination_folder(root,value)
    target_dir.mkdir(parents=True,exist_ok=True)
    target=target_dir/source.name
    if target.resolve()==source.resolve():
        return source
    if target.exists():
        raise FileExistsError(target)
    return Path(shutil.move(str(source),str(target)))

def iter_dated_files(archive_root:str|Path):
    root=Path(archive_root)
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            value,_=filename_date(path.name)
        except ValueError:
            continue
        yield value,path

def latest_file(archive_root:str|Path)->tuple[date,Path]:
    candidates=list(iter_dated_files(archive_root))
    if not candidates:
        raise FileNotFoundError(f"Δεν βρέθηκε περιοδικό με ημερομηνία στο {archive_root}")
    candidates.sort(key=lambda item:(item[0],item[1].stat().st_mtime_ns,str(item[1])))
    return candidates[-1]

def create_next_from_latest(archive_root:str|Path,*,target_date:date|None=None)->Path:
    latest_date,source=latest_file(archive_root)
    target=target_date or (latest_date+timedelta(days=1))
    if target<=latest_date:
        raise ValueError(f"Η νέα ημερομηνία {target.isoformat()} πρέπει να είναι μετά από {latest_date.isoformat()}.")
    new_name=replace_filename_date(source.name,target)
    target_dir=destination_folder(archive_root,target)
    target_dir.mkdir(parents=True,exist_ok=True)
    destination=target_dir/new_name
    if destination.exists():
        return destination
    shutil.copy2(source,destination)
    return destination
SERIES_FOLDERS=(
 ("ΑΝΑΦΟΡΕΣ ΑΞ.ΥΠ.","ΑΝΑΦΟΡΕΣ ","ΑΞ.ΥΠ."),
 ("ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α.","ΝΕΑ ΠΡΩΙΝΗ ΑΝΑΦΟΡΕΣ Γ.Α.",""),
 ("ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ","ΣΤΟΙΧΕΙΑ ΕΓΚΛΗΜΑΤΙΚΟΤΗΤΑΣ ",""),
)

def series_folder_for_filename(filename:str)->str:
    folded=normalize_text(filename)
    if folded.startswith("NEA PROINI ANAFOR"):
        return SERIES_FOLDERS[1][0]
    for folder,prefix,required in SERIES_FOLDERS:
        if folded.startswith(normalize_text(prefix)) and (not required or normalize_text(required) in folded):
            return folder
    raise ValueError(f"Το αρχείο δεν αντιστοιχεί σε γνωστή σειρά: {filename}")

def separate_series_file(source_file:str|Path,common_root:str|Path)->Path:
    source=Path(source_file)
    series=series_folder_for_filename(source.name)
    return move_orphan_into_archive(source,Path(common_root)/series)
