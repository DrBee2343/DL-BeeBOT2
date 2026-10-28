import re
from datetime import date, datetime

STATES = {
    "abia": "ABIA", "adamawa": "ADAMAWA", "akwa ibom": "AKWA IBOM", "anambra": "ANAMBRA",
    "bauchi": "BAUCHI", "bayelsa": "BAYELSA", "benue": "BENUE", "borno": "BORNO",
    "cross river": "CROSS RIVER", "delta": "DELTA", "ebonyi": "EBONYI", "edo": "EDO",
    "ekiti": "EKITI", "enugu": "ENUGU", "gombe": "GOMBE", "imo": "IMO", "jigawa": "JIGAWA",
    "kaduna": "KADUNA", "kano": "KANO", "katsina": "KATSINA", "kebbi": "KEBBI",
    "kogi": "KOGI", "kwara": "KWARA", "lagos": "LAGOS", "nasarawa": "NASARAWA",
    "niger": "NIGER", "ogun": "OGUN", "ondo": "ONDO", "osun": "OSUN", "oyo": "OYO",
    "plateau": "PLATEAU", "rivers": "RIVERS", "sokoto": "SOKOTO", "taraba": "TARABA",
    "yobe": "YOBE", "zamfara": "ZAMFARA", "fct": "FCT", "abuja": "FCT",
    "federal capital territory": "FCT",
}

DATE_FORMATS = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d %b %Y", "%d %B %Y")


def parse_date(raw: str) -> str:
    raw = raw.strip().replace(",", "")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {raw!r}")


def add_years(d: str, years: int) -> str:
    dt = datetime.strptime(d, "%d-%m-%Y")
    return dt.replace(year=dt.year + years).strftime("%d-%m-%Y")


def norm_state(raw: str) -> str:
    key = re.sub(r"\s+", " ", raw.strip().lower()).replace(" state", "")
    if key not in STATES:
        raise ValueError(f"Unknown state: {raw!r}")
    return STATES[key]


def norm_sex(raw: str) -> str:
    v = raw.strip().upper()[:1]
    if v not in ("M", "F"):
        raise ValueError(f"Sex must be M or F: {raw!r}")
    return v


def norm_height(raw: str) -> str:
    v = re.sub(r"[^0-9.]", "", raw.strip())
    if not v:
        raise ValueError("Height required")
    n = float(v)
    if n > 10:                       # given in centimetres, e.g. 198
        n = n / 100
    if not 1.0 <= n <= 2.5:
        raise ValueError(f"Height out of range: {raw!r}")
    return f"{n:.2f}M"


def norm_phone(raw: str) -> str:
    v = re.sub(r"[^0-9+]", "", raw.strip())
    if v.startswith("+234"):
        v = "0" + v[4:]
    if v.startswith("234") and len(v) == 13:
        v = "0" + v[3:]
    if not re.fullmatch(r"0\d{10}", v):
        raise ValueError(f"Phone must be 11 digits starting 0: {raw!r}")
    return v


def norm_name(first: str, middle: str, last: str) -> str:
    parts = " ".join(p for p in (first.strip(), middle.strip()) if p)
    return f"{last.strip().upper()}, {parts.upper()}"
