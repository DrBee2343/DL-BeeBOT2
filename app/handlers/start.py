from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.keyboards import main_menu
from app.services.credits import ensure_user, free_left

router = Router(name="start")

WELCOME = (
    "*Welcome.*\n\n"
    "Drop me your details and I'll turn them into a finished design "
    "in seconds.\n\n"
    "Tap a button below to begin."
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = await ensure_user(message.from_user)
    await message.answer(WELCOME, reply_markup=main_menu(await free_left(user.id)))


@router.callback_query(F.data == "nav:home")
async def go_home(cb: CallbackQuery) -> None:
    user = await ensure_user(cb.from_user)
    await cb.message.edit_text(WELCOME, reply_markup=main_menu(await free_left(user.id)))
    await cb.answer()
