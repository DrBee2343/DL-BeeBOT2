import asyncio
import json
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import dispose, init_models
from app.handlers import billing, generate, start
from app.middlewares.errors import ErrorMiddleware
from app.middlewares.throttle import ThrottleMiddleware
from app.services.dedupe import close_redis, first_time, get_redis

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("bot")

storage = RedisStorage.from_url(settings.redis_url)
dp = Dispatcher(storage=storage)
dp.update.outer_middleware(ErrorMiddleware())
dp.update.outer_middleware(ThrottleMiddleware())
dp.include_router(start.router)
dp.include_router(generate.router)
dp.include_router(billing.router)

bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def _process(update: Update) -> None:
    try:
        await dp.feed_update(bot, update)
    except Exception:  # noqa: BLE001
        log.exception("feed_update failed: %s", update.update_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await get_redis()
    await bot.set_webhook(
        settings.webhook_url,
        drop_pending_updates=True,
        allowed_updates=dp.resolve_used_update_types(),
    )
    log.info("webhook set -> %s", settings.webhook_url)
    yield
    await bot.delete_webhook()
    await bot.session.close()
    await close_redis()
    await dispose()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request) -> dict:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    if await first_time(update.update_id):
        asyncio.create_task(_process(update))
    return {"ok": True}


@app.post("/paystack/webhook")
async def paystack_webhook(request: Request) -> JSONResponse:
    raw = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    if not billing.verify_signature(raw, signature):
        return JSONResponse({"ok": False}, status_code=401)
    asyncio.create_task(billing.handle_event(json.loads(raw)))
    return JSONResponse({"ok": True})
