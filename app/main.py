import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
from fastapi import FastAPI, Request

from app.config import settings
from app.handlers import start
from app.middlewares.errors import ErrorMiddleware
from app.services.dedupe import get_redis, first_time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("bot")

storage = RedisStorage.from_url(settings.redis_url)
dp = Dispatcher(storage=storage)
dp.update.outer_middleware(ErrorMiddleware())
dp.include_router(start.router)

bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))


async def _process(update: Update) -> None:
    try:
        await dp.feed_update(bot, update)
    except Exception:
        log.exception("feed_update_failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_redis()
    await bot.set_webhook(
        settings.webhook_url,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )
    log.info("webhook set -> %s", settings.webhook_url)
    yield
    await bot.delete_webhook(drop_pending_updates=False)
    await bot.session.close()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post(settings.webhook_path)
async def webhook(request: Request) -> dict:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    if await first_time(update.update_id):
        asyncio.create_task(_process(update))
    return {"ok": True}
