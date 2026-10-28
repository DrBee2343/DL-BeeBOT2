from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from app.render.spec import ImageSlot, TemplateSpec, TextSlot

FONT_DIR = Path("assets/fonts")
TPL_DIR = Path("templates")
K5 = np.ones((5, 5), np.uint8)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def _text_w(draw, text: str, font, spacing: float) -> int:
    if not spacing:
        return int(draw.textlength(text, font=font))
    return int(sum(draw.textlength(c, font=font) + spacing for c in text) - spacing)


def _wrap(draw, text: str, font, max_w: int, spacing: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if _text_w(draw, trial, font, spacing) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
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
    for char in text:
        draw.text((cx, y), char, font=font, fill=fill)
        cx += draw.textlength(char, font=font) + spacing


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


def _ink_mask(crop: np.ndarray, ink: str) -> np.ndarray:
    if ink == "light":
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        mask = (gray > int(np.median(gray)) + 35).astype(np.uint8)
    elif ink == "red":
        r, g, b = (crop[:, :, i].astype(int) for i in range(3))
        mask = ((r - g > 40) & (r - b > 40)).astype(np.uint8)
    else:
        gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        mask = (gray < int(np.median(gray)) - 35).astype(np.uint8)
    return cv2.dilate(mask, K5, iterations=2)


def _scrub(base: Image.Image, slot) -> None:
    """Remove the plate's existing value so the new one stamps onto clean card."""
    x1, y1, x2, y2 = slot.box
    crop = np.array(base.crop(slot.box).convert("RGB"))
    ink = getattr(slot, "ink", "dark")

    if ink == "none":
        return

    if ink == "ghost":
        low = cv2.blur(crop, (41, 41))
        high = crop.astype(np.int16) - low.astype(np.int16)
        full = np.full(crop.shape[:2], 255, np.uint8)
        cleaned = np.clip(
            cv2.inpaint(low, full, 15, cv2.INPAINT_TELEA).astype(np.int16) + high, 0, 255
        ).astype(np.uint8)
    else:
        mask = _ink_mask(crop, ink)
        if not mask.any():
            return
        cleaned = cv2.inpaint(crop, mask, 4, cv2.INPAINT_TELEA)

    base.paste(Image.fromarray(cleaned), (x1, y1))


def _paste_image(base: Image.Image, src: Image.Image, slot: ImageSlot) -> None:
    x1, y1, x2, y2 = slot.box
    w, h = x2 - x1, y2 - y1
    img = src.convert("RGBA")

    if slot.desaturate:
        img = ImageEnhance.Contrast(img.convert("L").convert("RGBA")).enhance(slot.contrast)

    ratio = max(w / img.width, h / img.height) if slot.fit == "cover" else min(
        w / img.width, h / img.height
    )
    img = img.resize(
        (max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS
    )
    left = (img.width - w) // 2
    top = (img.height - h) // 2
    img = img.crop((left, top, left + w, top + h))

    if slot.opacity < 1.0:
        img.putalpha(img.getchannel("A").point(lambda v: int(v * slot.opacity)))

    if slot.mask in ("circle", "rounded"):
        shape = Image.new("L", (w, h), 0)
        pen = ImageDraw.Draw(shape)
        if slot.mask == "circle":
            pen.ellipse((0, 0, w - 1, h - 1), fill=255)
        else:
            pen.rounded_rectangle((0, 0, w - 1, h - 1), slot.radius, fill=255)
        img.putalpha(Image.composite(img.getchannel("A"), Image.new("L", (w, h), 0), shape))

    base.paste(img, (x1, y1), img)


def render(
    spec: TemplateSpec,
    values: dict,
    out: Path,
    photos: dict[str, Image.Image] | None = None,
    mode: str = "card",
) -> Path:
    photos = photos or {}
    base = Image.open(TPL_DIR / spec.plate).convert("RGBA")

    for slot in spec.slots:
        if slot.patch:
            _scrub(base, slot)

    for slot in spec.image_slots():
        if slot.behind_text and slot.key in photos:
            _paste_image(base, photos[slot.key], slot)

    for slot in spec.image_slots():
        if not slot.behind_text and slot.key in photos:
            _paste_image(base, photos[slot.key], slot)

    draw = ImageDraw.Draw(base)
    for slot in spec.text_slots():
        value = str(values.get(slot.key, "") or "").strip()
        if value:
            _stamp_text(draw, value, slot)

    if mode == "flat" and spec.bezel_crop:
        base = base.crop(spec.bezel_crop)

    out.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(out, "JPEG", quality=95, subsampling=0, optimize=True)
    return out
