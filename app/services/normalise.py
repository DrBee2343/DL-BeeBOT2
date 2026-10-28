import random
import re
from datetime import datetime

from app.config import settings

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
LNO_RE = re.compile(r"^[A-Z]{3}\d{4,5}[A-Z]{2}\d{2}$")


class ValidationError(ValueError):
    pass


def parse_date(raw: str) -> str:
    cleaned = raw.strip().replace(",", "")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    raise ValidationError("Use a date like 14-03-1998")


def add_years(ddmmyyyy: str, years: int) -> str:
    dt = datetime.strptime(ddmmyyyy, "%d-%m-%Y")
    return dt.replace(year=dt.year + years).strftime("%d-%m-%Y")


def norm_state(raw: str) -> str:
    key = re.sub(r"\s+", " ", raw.strip().lower()).replace(" state", "")
    if key not in STATES:
        raise ValidationError("That isn't a Nigerian state. Try e.g. Lagos or Oyo")
    return STATES[key]


def norm_sex(raw: str) -> str:
    value = raw.strip().upper()[:1]
    if value not in ("M", "F"):
        raise ValidationError("Send M or F")
    return value


def norm_height(raw: str) -> str:
    value = re.sub(r"[^0-9.]", "", raw.strip())
    if not value:
        raise ValidationError("Send your height, e.g. 1.78")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValidationError("Send your height, e.g. 1.78") from exc
    if number > 10:
        number /= 100
    if not 1.0 <= number <= 2.5:
        raise ValidationError("Height should be between 1.00 and 2.50 metres")
    return f"{number:.2f}M"


def norm_phone(raw: str) -> str:
    value = re.sub(r"[^0-9+]", "", raw.strip())
    if value.startswith("+234"):
        value = "0" + value[4:]
    elif value.startswith("234") and len(value) == 13:
        value = "0" + value[3:]
    if not re.fullmatch(r"0\d{10}", value):
        raise ValidationError("Send an 11-digit number starting with 0")
    return value


def norm_upper(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw.strip()).upper()
    if not value:
        raise ValidationError("This can't be empty")
    return value


def norm_text(raw: str) -> str:
    value = re.sub(r"\s+", " ", raw.strip())
    if not value:
        raise ValidationError("This can't be empty")
    return value


def norm_lno(raw: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]", "", raw.strip()).upper()
    if not LNO_RE.fullmatch(value):
        raise ValidationError("Format is 3 letters, 4-5 digits, 2 letters, 2 digits")
    return value


def gen_lno() -> str:
    letters = lambda n: "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=n))  # noqa: E731
    digits = lambda n: "".join(random.choices("0123456789", k=n))  # noqa: E731
    return f"{letters(3)}{digits(5)}{letters(2)}{digits(2)}"


VALIDATORS = {
    "date": parse_date,
    "state": norm_state,
    "sex": norm_sex,
    "height": norm_height,
    "phone": norm_phone,
    "upper": norm_upper,
    "text": norm_text,
    "lno": norm_lno,
}


def validate(kind: str, raw: str) -> str:
    fn = VALIDATORS.get(kind, norm_text)
    return fn(raw)


def state_code(state: str) -> str:
    return state.split()[0][:3].upper()


def build_values(inputs: dict) -> dict:
    """Turn collected user inputs into final render values."""
    state = inputs["state"]
    iss = inputs.get("iss") or datetime.now().strftime("%d-%m-%Y")
    exp = inputs.get("exp") or add_years(iss, settings.default_validity_years)

    surname = inputs["surname"].upper()
    given = " ".join(
        part for part in (inputs.get("firstname", ""), inputs.get("middlename", "")) if part
    ).upper()

    address_lines = [line.strip().upper() for line in inputs["address"].splitlines() if line.strip()]
    if not address_lines or state.split()[0] not in address_lines[-1]:
        address_lines.append(state.split()[0])

    return {
        "lno": inputs.get("lno") or gen_lno(),
        "state_full": f"{state} STATE",
        "state_code": state_code(state),
        "dob": inputs["dob"],
        "iss": iss,
        "exp": exp,
        "name": f"{surname}, {given}".strip().rstrip(","),
        "address": "\n".join(address_lines[:3]),
        "sex": inputs["sex"],
        "ht": inputs["ht"],
        "bl": inputs.get("bl", "O-"),
        "fmarks": inputs.get("fmarks", "N"),
        "gl": inputs.get("gl", "N"),
        "rep": inputs.get("rep", "0"),
        "ren": inputs.get("ren", "1"),
        "end": inputs.get("end", "P"),
        "nok": inputs["nok"],
        "first_iss": inputs["first_iss"],
        "holder_sign": f"{inputs.get('firstname', '').title()} {surname.title()}".strip(),
    }
