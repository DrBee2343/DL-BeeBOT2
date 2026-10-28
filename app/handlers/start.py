from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from app.keyboards import back_home, main_menu
from app.services import credits
from app.texts import HELP, WELCOME

router = Router(name="start")


async def _home_text(user_id: int) -> tuple[str, object]:
    free = await credits.free_left(user_id)
    bal = await credits.balance(user_id)
    return WELCOME, main_menu(free, bal)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await credits.ensure_user(message.from_user)
    text, kb = await _home_text(message.from_user.id)
    await message.answer(text, reply_markup=kb)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await credits.ensure_user(message.from_user)
    await message.answer(HELP, reply_markup=back_home())


@router.callback_query(F.data == "nav:help")
async def cb_help(cb: CallbackQuery) -> None:
    await cb.message.edit_text(HELP, reply_markup=back_home())
    await cb.answer()


@router.callback_query(F.data == "nav:home")
async def cb_home(cb: CallbackQuery) -> None:
    await credits.ensure_user(cb.from_user)
    text, kb = await _home_text(cb.from_user.id)
    await cb.message.edit_text(text, reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "me:stats")
async def cb_stats(cb: CallbackQuery) -> None:
    free = await credits.free_left(cb.from_user.id)
    bal = await credits.balance(cb.from_user.id)
    await cb.answer(f"Free generations left: {free}\nCredits: {bal}", show_alert=True)
