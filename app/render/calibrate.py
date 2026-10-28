"""python -m app.render.calibrate ng_dl [--diff original.png] [--boxes]"""
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from app.render.pipeline import ASSET_DIR, render
from app.render.spec import TemplateSpec

SPECS = Path("templates")


def main() -> None:
    tpl_id = sys.argv[1]
    spec = TemplateSpec.model_validate_json((SPECS / tpl_id / "spec.json").read_text())
    out = Path("debug") / f"{tpl_id}_render.png"
    out.parent.mkdir(exist_ok=True)

    values = {s.key: s.label or s.key.upper() for s in spec.text_slots()}
    photos = {s.key: Image.open("debug/sample_face.png") for s in spec.image_slots()}

    render(spec, values, out, photos=photos, mode="card")

    if "--boxes" in sys.argv:
        dbg = Image.open(out).convert("RGB")
        d = ImageDraw.Draw(dbg)
        for s in spec.slots:
            x1, y1, x2, y2 = s.box
            d.rectangle((x1, y1, x2, y2), outline="#ff00ff", width=3)
            d.text((x1 + 4, y1 + 4), s.key, fill="#ff00ff")
        dbg.save(Path("debug") / f"{tpl_id}_boxes.png")

    if "--diff" in sys.argv:
        ref = Image.open(sys.argv[sys.argv.index("--diff") + 1]).convert("RGB")
        ref = ref.resize(spec.canvas, Image.LANCZOS)
        blend = Image.blend(ref, Image.open(out).convert("RGB"), 0.5)
        blend.save(Path("debug") / f"{tpl_id}_blend.png")
        ImageChops.difference(ref, Image.open(out).convert("RGB")).save(
            Path("debug") / f"{tpl_id}_delta.png")

    print(f"wrote {out}")


if __name__ == "__main__":
    main()
