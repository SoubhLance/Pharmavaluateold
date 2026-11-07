import re
BATCH = re.compile(r"\b(?:B(?:ATCH)?\.?\s*(?:NO\.?)?\s*:?\s*)?([A-Z]{0,3}\d{3,8}[A-Z]?)\b", re.I)
DATE = re.compile(r"\b(0?[1-9]|1[0-2])\s*[/\-.]\s*((?:20)?\d{2})\b")
def parse_expiry(text):
    m = DATE.search(text)
    if not m: return None
    mo, yr = int(m.group(1)), int(m.group(2)); yr = yr + 2000 if yr < 100 else yr
    return mo, yr
def check_text(text, ref_name=None, mfg_year_range=(2015, 2035)):
    flags = []
    e = parse_expiry(text)
    if e is None: flags.append("expiry_unreadable")
    elif not (mfg_year_range[0] <= e[1] <= mfg_year_range[1]): flags.append("expiry_implausible")
    if not BATCH.search(text): flags.append("batch_unreadable")
    if ref_name:
        from difflib import SequenceMatcher
        best = max((SequenceMatcher(None, ref_name.lower(), w.lower()).ratio() for w in text.split()), default=0)
        if best < 0.75: flags.append("name_mismatch")
    return flags
