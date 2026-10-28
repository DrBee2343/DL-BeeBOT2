from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup as KB
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.render.spec import TemplateSpec


def main_menu(free_left: int, credits: int) -> KB:
    return KB(inline_keyboard=[
        [Btn(text="Create an image", callback_data="gen:start")],
        [Btn(text="My designs", callback_data="me:designs"),
         Btn(text="Buy credits", callback_data="bill:plans")],
        [Btn(text=f"Free: {free_left}   Credits: {credits}", callback_data="me:stats")],
        [Btn(text="Help", callback_data="nav:help")],
    ])


def template_list(specs: tuple[TemplateSpec, ...]) -> KB:
    b = InlineKeyboardBuilder()
    for spec in specs:
        b.row(Btn(text=spec.name, callback_data=f"tpl:{spec.id}"))
    b.row(Btn(text="Cancel", callback_data="nav:home"))
    return b.as_markup()


def background_menu() -> KB:
    return KB(inline_keyboard=[
        [Btn(text="White background", callback_data="bg:white")],
        [Btn(text="Keep original", callback_data="bg:keep")],
        [Btn(text="Cancel", callback_data="nav:home")],
    ])


def ask_menu(show_random: bool = False, show_skip: bool = False) -> KB:
    rows = []
    if show_random:
        rows.append([Btn(text="Generate random", callback_data="ask:random")])
    if show_skip:
        rows.append([Btn(text="Use default", callback_data="ask:default")])
    rows.append([Btn(text="Cancel", callback_data="nav:home")])
    return KB(inline_keyboard=rows)


def confirm_card(spec: TemplateSpec, values: dict) -> KB:
    rows = []
    for slot in spec.editable_slots():
        raw = str(values.get(slot.key, "") or "").replace("\n", " ")
        shown = raw if len(raw) <= 30 else raw[:29] + "…"
        rows.append([Btn(text=f"{slot.label}: {shown or '—'}", callback_data=f"edit:{slot.key}")])
    rows.append([Btn(text="Generate", callback_data="gen:render")])
    rows.append([Btn(text="Start over", callback_data="nav:home")])
    return KB(inline_keyboard=rows)


def result_actions(render_id: int) -> KB:
    return KB(inline_keyboard=[
        [Btn(text="Tweak it", callback_data=f"tw:{render_id}"),
         Btn(text="Regenerate", callback_data=f"rg:{render_id}")],
        [Btn(text="New image", callback_data="gen:start")],
    ])


def edit_menu(render_id: int, spec: TemplateSpec) -> KB:
    b = InlineKeyboardBuilder()
    for slot in spec.editable_slots():
        b.row(Btn(text=slot.label, callback_data=f"ed:{render_id}:{slot.key}"))
    b.row(Btn(text="Back", callback_data=f"back:{render_id}"))
    return b.as_markup()


def plans_menu(plans: list[tuple[str, int, int]]) -> KB:
    """plans = [(label, credits, price_kobo), ...]"""
    b = InlineKeyboardBuilder()
    for label, credits, _ in plans:
        b.row(Btn(text=label, callback_data=f"buy:{credits}"))
    b.row(Btn(text="Pay with crypto", callback_data="buy:crypto"))
    b.row(Btn(text="Back", callback_data="nav:home"))
    return b.as_markup()


def back_home() -> KB:
    return KB(inline_keyboard=[[Btn(text="Home", callback_data="nav:home")]])
