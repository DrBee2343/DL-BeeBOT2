from aiogram.types import InlineKeyboardButton as B, InlineKeyboardMarkup as KB
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.render.spec import TemplateSpec

BACK = B(text="Back", callback_data="nav:back")
HOME = B(text="Home", callback_data="nav:home")


def main_menu(free_left: int) -> KB:
    return KB(inline_keyboard=[
        [B(text="Create an image", callback_data="gen:start")],
        [
            B(text="My designs", callback_data="me:designs"),
            B(text="Credits", callback_data="bill:plans"),
        ],
        [B(text=f"Free left: {free_left}", callback_data="me:stats"),
         B(text="Help", callback_data="nav:help")],
    ])


def template_list(specs: list[TemplateSpec]) -> KB:
    b = InlineKeyboardBuilder()
    for s in specs:
        b.row(B(text=s.name, callback_data=f"tpl:{s.id}"))
    b.row(B(text="Cancel", callback_data="nav:home"))
    return b.as_markup()


def confirm_card(spec: TemplateSpec, values: dict) -> KB:
    rows = [
        [B(text=f"{slot.label}: {values.get(slot.key, '-')[:28]}",
           callback_data=f"edit:{slot.key}")]
        for slot in spec.editable_slots()
    ]
    rows.append([B(text="Looks good - Generate", callback_data="gen:render")])
    rows.append([B(text="Start over", callback_data="nav:home")])
    return KB(inline_keyboard=rows)


def result_actions(render_id: int) -> KB:
    return KB(inline_keyboard=[
        [
            B(text="Tweak it", callback_data=f"tw:{render_id}"),
            B(text="Regenerate", callback_data=f"rg:{render_id}"),
        ],
        [
            B(text="Download HD", callback_data=f"hd:{render_id}"),
            B(text="New image", callback_data="gen:start"),
        ],
    ])


def back_home() -> KB:
    return KB(inline_keyboard=[[BACK, HOME]])
