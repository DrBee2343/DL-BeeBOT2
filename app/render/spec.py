from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BaseSlot(BaseModel):
    key: str
    label: str = ""
    box: tuple[int, int, int, int]          # x1, y1, x2, y2 — absolute
    required: bool = False
    patch: bool = True                      # erase old value from eraser plate first


class TextSlot(BaseSlot):
    type: Literal["text"] = "text"
    font: str = "RobotoCondensed-Regular.ttf"
    size: int = 52
    color: str = "#1a1a1a"
    align: Literal["left", "center", "right"] = "left"
    valign: Literal["top", "middle", "bottom"] = "middle"
    max_lines: int = 1
    line_height: float = 1.18
    min_size: int = 20
    uppercase: bool = False
    letter_spacing: float = 0.0


class ImageSlot(BaseSlot):
    type: Literal["image"] = "image"
    fit: Literal["cover", "contain"] = "cover"
    mask: Literal["none", "circle", "rounded"] = "none"
    radius: int = 0
    opacity: float = 1.0
    desaturate: bool = False
    contrast: float = 1.0
    behind_text: bool = False


Slot = Annotated[Union[TextSlot, ImageSlot], Field(discriminator="type")]


class TemplateSpec(BaseModel):
    id: str
    name: str
    canvas: tuple[int, int]
    plate: str                                # master plate, static content intact
    eraser: str | None = None                 # clean plate, patches old values
    slots: list[Slot]
    bezel_crop: tuple[int, int, int, int] | None = None   # FLAT mode only

    def text_slots(self) -> list[TextSlot]:
        return [s for s in self.slots if isinstance(s, TextSlot)]

    def image_slots(self) -> list[ImageSlot]:
        return [s for s in self.slots if isinstance(s, ImageSlot)]
