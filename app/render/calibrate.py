"""python -m app.render.calibrate ng_dl [--boxes] [--diff reference.png] [--flat]"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from app.render.pipeline import render
from app.render.spec import TemplateSpec
from app.services.normalise import build_values

TPL_DIR = Path("templates")
DEBUG = Path("debug")

SAMPLE = {
    "surname": "DUROSARO",
    "firstname": "ABDULBAASIT",
    "middlename": "ADETUNJI",
    "dob": "03-11-2006",
    "address": "SAGBON COMPOUND\nOKE AGBENI",
    "state": "OYO",
    "sex": "M",
    "ht": "1.98M",
    "nok": "08134567890",
    "first_iss": "10-06-2022",
    "lno": "ABC03746AA06",
}


def main() -> None:
    template_id = sys.argv[1]
    spec = TemplateSpec.model_validate_json((TPL_DIR / template_id / "spec.json").read_text())

    DEBUG.mkdir(exist_ok=True)
    out = DEBUG / f"{template_id}_render.png"

    values = build_values(SAMPLE)
    photos = {}
    face = DEBUG / "sample_face.png"
    if face.exists():
        portrait = Image.open(face).convert("RGBA")
        photos = {slot.key: portrait for slot in spec.image_slots()}

    render(spec, values, out, photos=photos, mode="flat" if "--flat" in sys.argv else "card")

    if "--boxes" in sys.argv:
        dbg = Image.open(out).convert("RGB")
        pen = ImageDraw.Draw(dbg)
        for slot in spec.slots:
            x1, y1, x2, y2 = slot.box
            pen.rectangle((x1, y1, x2, y2), outline="#ff00ff", width=3)
            pen.text((x1 + 4, y1 + 4), slot.key, fill="#ff00ff")
        dbg.save(DEBUG / f"{template_id}_boxes.png")

    if "--diff" in sys.argv:
        ref = Image.open(sys.argv[sys.argv.index("--diff") + 1]).convert("RGB")
        ref = ref.resize(spec.canvas, Image.LANCZOS)
        cur = Image.open(out).convert("RGB")
        Image.blend(ref, cur, 0.5).save(DEBUG / f"{template_id}_blend.png")
        ImageChops.difference(ref, cur).save(DEBUG / f"{template_id}_delta.png")

    print(f"wrote {out}")


if __name__ == "__main__":
    main()
