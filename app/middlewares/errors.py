import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import settings
from app.texts import GENERIC_ERROR

log = logging.getLogger("errors")


class ErrorMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:  # noqa: BLE001
            log.exception("handler failed")
            await self._tell_user(event)
            await self._tell_admins(event, exc)
            return None

    async def _tell_user(self, event: TelegramObject) -> None:
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(GENERIC_ERROR, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(GENERIC_ERROR)
        except Exception:  # noqa: BLE001
            pass

    async def _tell_admins(self, event: TelegramObject, exc: Exception) -> None:
        bot = getattr(event, "bot", None)
        if bot is None or not settings.admins:
            return
        text = f"<b>{type(exc).__name__}</b>\n<code>{exc}</code>"
        for admin in settings.admins:
            try:
                await bot.send_message(admin, text)
            except Exception:  # noqa: BLE001
                pass
