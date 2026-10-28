from functools import lru_cache

import numpy as np
from PIL import Image

from app.config import settings


@lru_cache
def _session():
    from rembg import new_session

    return new_session("u2net_human_seg")


def cutout(image: Image.Image, background: str = "white") -> Image.Image:
    from rembg import remove

    rgba = remove(image.convert("RGBA"), session=_session(), post_process_mask=True)

    if background == "keep":
        return rgba

    colour = (255, 255, 255, 255) if background == "white" else (238, 238, 234, 255)
    canvas = Image.new("RGBA", rgba.size, colour)
    canvas.alpha_composite(rgba)
    return canvas


def cutout_white(image: Image.Image) -> Image.Image:
    return cutout(image, "white")
