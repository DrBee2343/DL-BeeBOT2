import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.config import settings
from app.db import session_scope
from app.keyboards import plans_menu
from app.models import Order
from app.services import credits
from app.states import Billing
from app.texts import PAID, PAYSTACK_OPEN, PLANS, PAID_PENDING

router = Router(name="billing")

PLANS = [
    ("10 credits — ₦1,500", 10, 150000),
    ("30 credits — ₦4,000", 30, 400000),
    ("100 credits — ₦12,000", 100, 1200000),
]

PAYSTACK_API = "https://api.paystack.co"


def verify_signature(raw: bytes, signature: str) -> bool:
    if not settings.paystack_secret_key or not signature:
        return False
    expected = hmac.new(settings.paystack_secret_key.encode(), raw, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.callback_query(F.data == "bill:plans")
async def show_plans(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Billing.picking)
    await cb.message.edit_text(PLANS, reply_markup=plans_menu(PLANS))
    await cb.answer()


@router.callback_query(Billing.picking, F.data.startswith("buy:"))
async def buy(cb: CallbackQuery) -> None:
    value = cb.data.split(":", 1)[1]
    if value == "crypto":
        await _crypto(cb)
        return
    await _paystack(cb, int(value))


async def _paystack(cb: CallbackQuery, credit_count: int) -> None:
    amount = next(p for _, c, p in PLANS if c == credit_count)
    reference = f"ps_{cb.from_user.id}_{uuid.uuid4().hex[:10]}"

    async with session_scope() as s:
        s.add(Order(user_id=cb.from_user.id, reference=reference, provider="paystack",
                    currency="NGN", amount=amount / 100, credits=credit_count))

    payload = {
        "email": f"{cb.from_user.id}@telegram.local",
        "amount": amount,
        "reference": reference,
        "channels": ["card", "bank", "ussd", "bank_transfer", "mobile_money"],
    }
    headers = {"Authorization": f"Bearer {settings.paystack_secret_key}"}

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(f"{PAYSTACK_API}/transaction/initialize", json=payload, headers=headers)
        data = resp.json()

    if not data.get("status"):
        await cb.answer("Paystack is unavailable right now.", show_alert=True)
        return

    from aiogram.types import InlineKeyboardButton as Btn, InlineKeyboardMarkup as KB

    await cb.message.edit_text(
        PAYSTACK_OPEN.format(amount=f"{amount / 100:,.0f}"),
        reply_markup=KB(inline_keyboard=[[
            Btn(text="Pay now", url=data["data"]["authorization_url"])
        ]]),
    )
    await cb.answer()


async def _crypto(cb: CallbackQuery) -> None:
    address = settings.crypto_usdt_bsc_address
    if not address:
        await cb.answer("No crypto wallet configured yet.", show_alert=True)
        return

    reference = f"cr_{cb.from_user.id}_{uuid.uuid4().hex[:10]}"
    amount = 3.0014
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)

    async with session_scope() as s:
        s.add(Order(user_id=cb.from_user.id, reference=reference, provider="crypto",
                    currency="USDT", network="BSC", amount=amount, credits=10,
                    pay_address=address, expires_at=expires))

    await cb.message.edit_text(
        PAID_PENDING.format(amount=amount, currency="USDT", address=address)
    )
    await cb.answer()


async def handle_event(payload: dict) -> None:
    if payload.get("event") != "charge.success":
        return
    reference = payload["data"]["reference"]
    await confirm_paystack(reference)


async def confirm_paystack(reference: str) -> bool:
    headers = {"Authorization": f"Bearer {settings.paystack_secret_key}"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{PAYSTACK_API}/transaction/verify/{reference}", headers=headers)
        data = resp.json()

    if not data.get("status") or data["data"]["status"] != "success":
        return False

    async with session_scope() as s:
        order = await s.scalar(Order.__table__.select().where(Order.reference == reference))
        if order is None:
            return False
        if order.status == "paid":
            return True
        order.status = "paid"
        order.paid_at = datetime.now(timezone.utc)
        user_id, credit_count = order.user_id, order.credits

    added = await credits.grant(user_id, credit_count, "purchase", ref=f"order:{reference}")
    if added:
        bal = await credits.balance(user_id)
        from app.main import bot

        await bot.send_message(user_id, PAID.format(credits=credit_count, balance=bal))
    return True
