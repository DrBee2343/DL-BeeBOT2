from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class BaseSlot(BaseModel):
    key: str
    box: tuple[int, int, int, int]
    required: bool = False
    patch: bool = True
    ink: Literal["dark", "light", "red", "ghost", "none"] = "dark"


class TextSlot(BaseSlot):
    type: Literal["text"] = "text"
    label: str = ""
    prompt: str = ""
    hint: str = ""
    validator: str = "text"
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
    default: str = ""
    editable: bool = True


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
    plate: str
    bezel_crop: tuple[int, int, int, int] | None = None
    cost: int = 1
    slots: list[Slot]

    def text_slots(self) -> list[TextSlot]:
        return [s for s in self.slots if isinstance(s, TextSlot)]

    def image_slots(self) -> list[ImageSlot]:
        return [s for s in self.slots if isinstance(s, ImageSlot)]

    def asked_slots(self) -> list[TextSlot]:
        return [s for s in self.slots if isinstance(s, TextSlot) and s.required]

    def editable_slots(self) -> list[TextSlot]:
        return [s for s in self.slots if isinstance(s, TextSlot) and s.editable]
