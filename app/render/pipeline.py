from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from app.render.spec import ImageSlot, TemplateSpec, TextSlot

FONT_DIR = Path("assets/fonts")
ASSET_DIR = Path("templates")


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _text_w(draw, text: str, font, spacing: float) -> int:
    if not spacing:
        return int(draw.textlength(text, font=font))
    return int(sum(draw.textlength(c, font=font) + spacing for c in text) - spacing)


def _wrap(draw, text: str, font, max_w: int, spacing: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if _text_w(draw, trial, font, spacing) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(draw, text: str, slot: TextSlot, max_w: int, max_h: int):
    for size in range(slot.size, slot.min_size - 1, -1):
        font = _font(slot.font, size)
        lines = _wrap(draw, text, font, max_w, slot.letter_spacing)
        lh = int(size * slot.line_height)
        if len(lines) <= slot.max_lines and len(lines) * lh <= max_h:
            return font, lines, lh
    font = _font(slot.font, slot.min_size)
    lines = _wrap(draw, text, font, max_w, slot.letter_spacing)[: slot.max_lines]
    return font, lines, int(slot.min_size * slot.line_height)


def _draw_line(draw, x: int, y: int, text: str, font, fill: str, spacing: float) -> None:
    if not spacing:
        draw.text((x, y), text, font=font, fill=fill)
        return
    cx = x
    for ch in text:
        draw.text((cx, y), ch, font=font, fill=fill)
        cx += draw.textlength(ch, font=font) + spacing


def _stamp_text(draw: ImageDraw.ImageDraw, text: str, slot: TextSlot) -> None:
    x1, y1, x2, y2 = slot.box
    w, h = x2 - x1, y2 - y1
    text = text.upper() if slot.uppercase else text

    font, lines, lh = _fit(draw, text, slot, w, h)
    block_h = len(lines) * lh

    if slot.valign == "top":
        cy = y1
    elif slot.valign == "bottom":
        cy = y2 - block_h
    else:
        cy = y1 + (h - block_h) // 2

    for line in lines:
        lw = _text_w(draw, line, font, slot.letter_spacing)
        if slot.align == "left":
            cx = x1
        elif slot.align == "right":
            cx = x2 - lw
        else:
            cx = x1 + (w - lw) // 2
        _draw_line(draw, cx, cy, line, font, slot.color, slot.letter_spacing)
        cy += lh


def _paste_image(base: Image.Image, src: Image.Image, slot: ImageSlot) -> None:
    x1, y1, x2, y2 = slot.box
    w, h = x2 - x1, y2 - y1
    img = src.convert("RGBA")

    if slot.desaturate:
        img = ImageEnhance.Contrast(img.convert("L").convert("RGBA")).enhance(slot.contrast)

    ratio = max(w / img.width, h / img.height) if slot.fit == "cover" \
        else min(w / img.width, h / img.height)
    img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)

    left = (img.width - w) // 2
    top = (img.height - h) // 2
    img = img.crop((left, top, left + w, top + h))

    if slot.opacity < 1.0:
        a = img.getchannel("A").point(lambda v: int(v * slot.opacity))
        img.putalpha(a)

    if slot.mask == "circle":
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, w - 1, h - 1), fill=255)
        img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (w, h), 0), mask))
    elif slot.mask == "rounded":
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), slot.radius, fill=255)
        img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (w, h), 0), mask))

    base.paste(img, (x1, y1), img)


def render(
    spec: TemplateSpec,
    values: dict,
    out: Path,
    photos: dict[str, Image.Image] | None = None,
    mode: str = "card",
) -> Path:
    photos = photos or {}
    base = Image.open(ASSET_DIR / spec.plate).convert("RGBA")
    eraser = Image.open(ASSET_DIR / spec.eraser).convert("RGBA") if spec.eraser else None

    # 1 — erase every dynamic region using the clean plate
    if eraser:
        for slot in spec.slots:
            if slot.patch:
                base.paste(eraser.crop(slot.box), (slot.box[0], slot.box[1]))

    # 2 — images that sit behind text (ghost portrait)
    for slot in spec.image_slots():
        if slot.behind_text and slot.key in photos:
            _paste_image(base, photos[slot.key], slot)

    # 3 — foreground images (portrait)
    for slot in spec.image_slots():
        if not slot.behind_text and slot.key in photos:
            _paste_image(base, photos[slot.key], slot)

    # 4 — text
    draw = ImageDraw.Draw(base)
    for slot in spec.text_slots():
        val = str(values.get(slot.key, "") or "").strip()
        if val:
            _stamp_text(draw, val, slot)

    # 5 — output framing
    if mode == "flat" and spec.bezel_crop:
        base = base.crop(spec.bezel_crop)

    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, "JPEG", quality=95, subsampling=0, optimize=True)
    return out
