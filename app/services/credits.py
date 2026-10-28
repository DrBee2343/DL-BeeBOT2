from sqlalchemy import func, select

from app.config import settings
from app.db import session_scope
from app.models import CreditLedger, User, utcnow


async def ensure_user(tg_user) -> User:
    async with session_scope() as s:
        user = await s.get(User, tg_user.id)
        if user is None:
            user = User(
                id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                language=tg_user.language_code,
                is_admin=tg_user.id in settings.admins,
            )
            s.add(user)
            await s.flush()
        else:
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            user.last_seen_at = utcnow()
        return user


async def _sum(s, user_id: int) -> int:
    total = await s.scalar(
        select(func.coalesce(func.sum(CreditLedger.delta), 0)).where(
            CreditLedger.user_id == user_id
        )
    )
    return int(total or 0)


async def balance(user_id: int) -> int:
    async with session_scope() as s:
        return await _sum(s, user_id)


async def free_left(user_id: int) -> int:
    async with session_scope() as s:
        user = await s.get(User, user_id)
        used = user.free_used if user else 0
    return max(0, settings.free_generations - used)


async def charge(user_id: int, cost: int, ref: str) -> str | None:
    """Returns 'free' or 'credits', or None when the user can't afford it."""
    async with session_scope() as s:
        user = await s.get(User, user_id, with_for_update=True)
        if user is None:
            return None
        if user.free_used < settings.free_generations:
            user.free_used += 1
            return "free"
        if await _sum(s, user_id) < cost:
            return None
        s.add(CreditLedger(user_id=user_id, delta=-cost, reason="render", ref=ref))
        return "credits"


async def refund(user_id: int, cost: int, ref: str, kind: str) -> None:
    async with session_scope() as s:
        if kind == "free":
            user = await s.get(User, user_id, with_for_update=True)
            if user and user.free_used > 0:
                user.free_used -= 1
            return
        if await s.scalar(select(CreditLedger.id).where(CreditLedger.ref == ref)):
            return
        s.add(CreditLedger(user_id=user_id, delta=cost, reason="refund", ref=ref))


async def grant(user_id: int, amount: int, reason: str, ref: str | None = None) -> bool:
    async with session_scope() as s:
        if ref and await s.scalar(select(CreditLedger.id).where(CreditLedger.ref == ref)):
            return False
        s.add(CreditLedger(user_id=user_id, delta=amount, reason=reason, ref=ref))
        return True
