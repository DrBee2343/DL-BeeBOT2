from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.render.spec import ImageSlot, TemplateSpec, TextSlot

FONT_DIR = Path("assets/fonts")


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    l, t, r, b = draw.textbbox((0, 0), text, font=font)
    return r - l, b - t


def _wrap(draw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if _measure(draw, trial, font)[0] <= max_w or not cur:
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
        lines = _wrap(draw, text, font, max_w)
        lh = int(size * 1.22)
        if len(lines) <= slot.max_lines and len(lines) * lh <= max_h:
            return font, lines, lh
    font = _font(slot.font, slot.min_size)
    return font, _wrap(draw, text, font, max_w)[: slot.max_lines], int(slot.min_size * 1.22)


def _draw_text(draw, canvas_w: int, text: str, slot: TextSlot) -> None:
    x, y, w, h = slot.box
    text = text.upper() if slot.uppercase else text
    font, lines, lh = _fit(draw, text, slot, w, h)
    block_h = len(lines) * lh

    if slot.valign == "top":
        cy = y
    elif slot.valign == "bottom":
        cy = y + h - block_h
    else:
        cy = y + (h - block_h) // 2

    for line in lines:
        lw = _measure(draw, line, font)[0]
        if slot.align == "left":
            cx = x
        elif slot.align == "right":
            cx = x + w - lw
        else:
            cx = x + (w - lw) // 2

        kwargs = {}
        if slot.stroke_width:
            kwargs = {"stroke_width": slot.stroke_width, "stroke_fill": slot.stroke_fill}
        if slot.shadow:
            draw.text((cx + 2, cy + 2), line, font=font, fill="#00000088", **kwargs)
        draw.text((cx, cy), line, font=font, fill=slot.color, **kwargs)
        cy += lh


def _place_photo(base: Image.Image, photo: Image.Image, slot: ImageSlot) -> None:
    x, y, w, h = slot.box
    ratio = max(w / photo.width, h / photo.height) if slot.fit == "cover" \
        else min(w / photo.width, h / photo.height)
    new = photo.resize((max(1, int(photo.width * ratio)), max(1, int(photo.height * ratio))), Image.LANCZOS)

    left = (new.width - w) // 2
    top = (new.height - h) // 2
    new = new.crop((left, top, left + w, top + h))

    if slot.mask == "circle":
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, w - 1, h - 1), fill=255)
    elif slot.mask == "rounded":
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), slot.radius, fill=255)
    else:
        mask = None

    base.paste(new, (x, y), mask)


def render(spec: TemplateSpec, values: dict, out: Path, photos: dict[str, Image.Image] | None = None) -> Path:
    canvas = Image.open(spec.base_art).convert("RGBA")
    if canvas.size != spec.canvas:
        canvas = canvas.resize(spec.canvas, Image.LANCZOS)

    photos = photos or {}
    for slot in spec.image_slots():
        if slot.key in photos:
            _place_photo(canvas, photos[slot.key].convert("RGBA"), slot)

    draw = ImageDraw.Draw(canvas)
    for slot in spec.text_slots():
        raw = str(values.get(slot.key, "") or "").strip()
        if raw:
            _draw_text(draw, canvas.width, raw, slot)

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "JPEG", quality=92, optimize=True)
    return out
