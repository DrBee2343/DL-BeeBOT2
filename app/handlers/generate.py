import asyncio
import time
import uuid
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.db import session_scope
from app.keyboards import ask_menu, background_menu, confirm_card, result_actions, template_list
from app.models import Render
from app.render.pipeline import render
from app.render.spec import TemplateSpec
from app.services import credits, templates
from app.services.dedupe import acquire_user_lock, release_user_lock
from app.services.normalise import ValidationError, build_values, gen_lno, validate
from app.states import GenFlow
from app.texts import (
    ASK,
    BG_WORKING,
    CANCELLED,
    CHOOSING_BG,
    CONFIRM,
    INVALID_INPUT,
    NO_CREDITS,
    PHOTO_RECEIVED,
    PICK_TEMPLATE,
    RENDER_DONE,
    RENDER_FAILED,
    RENDERING,
    SEND_PHOTO,
)

router = Router(name="generate")

_sem = asyncio.Semaphore(settings.max_concurrent_renders)


async def _spec(data: dict) -> TemplateSpec:
    return templates.load(data["template_id"])


@router.callback_query(F.data == "gen:start")
async def start_generation(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(GenFlow.picking)
    await cb.message.edit_text(PICK_TEMPLATE, reply_markup=template_list(templates.all_templates()))
    await cb.answer()


@router.callback_query(GenFlow.picking, F.data.startswith("tpl:"))
async def pick_template(cb: CallbackQuery, state: FSMContext) -> None:
    template_id = cb.data.split(":", 1)[1]
    spec = templates.load(template_id)
    await state.update_data(template_id=template_id, inputs={}, values={}, photo=None)
    await state.set_state(GenFlow.photo)
    await cb.message.edit_text(SEND_PHOTO, reply_markup=ask_menu())
    await cb.answer()


@router.message(GenFlow.photo, F.photo)
async def got_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    file = await bot.get_file(message.photo[-1].file_id)
    buffer = await bot.download_file(file.file_path)

    from PIL import Image

    image = Image.open(buffer).convert("RGB")
    await state.update_data(photo=image)
    await state.set_state(GenFlow.background)
    await message.answer(PHOTO_RECEIVED, reply_markup=background_menu())


@router.message(GenFlow.photo)
async def photo_hint(message: Message) -> None:
    await message.answer("Send a photo, or tap Cancel.")


@router.callback_query(GenFlow.background, F.data.startswith("bg:"))
async def pick_background(cb: CallbackQuery, state: FSMContext) -> None:
    choice = cb.data.split(":", 1)[1]
    await cb.message.edit_text(BG_WORKING)

    data = await state.get_data()
    image = data.get("photo")
    if image is not None and choice == "white":
        from app.services.cutout import cutout_white

        loop = asyncio.get_running_loop()
        image = await loop.run_in_executor(None, cutout_white, image)
    await state.update_data(photo=image, background=choice)

    await state.set_state(GenFlow.fields)
    await cb.answer()
    await _ask_next(cb.message, state, edit=False)


async def _ask_next(message: Message, state: FSMContext, edit: bool = True) -> None:
    data = await state.get_data()
    spec = await _spec(data)
    inputs = data.get("inputs", {})

    pending = [s for s in spec.asked_slots() if s.key not in inputs]
    if not pending:
        await _show_confirm(message, state, edit=edit)
        return

    slot = pending[0]
    text = ASK.format(label=slot.label, prompt=slot.prompt, hint=slot.hint or "-")
    kb = ask_menu(show_random=slot.key == "lno", show_skip=bool(slot.default))
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(GenFlow.fields, F.data == "ask:random")
async def ask_random(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    inputs = data.get("inputs", {})
    inputs["lno"] = gen_lno()
    await state.update_data(inputs=inputs)
    await cb.message.edit_text(f"Licence number: <code>{inputs['lno']}</code>")
    await _ask_next(cb.message, state)
    await cb.answer()


@router.callback_query(GenFlow.fields, F.data == "ask:default")
async def ask_default(cb: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    spec = await _spec(data)
    inputs = data.get("inputs", {})
    pending = [s for s in spec.asked_slots() if s.key not in inputs]
    if not pending:
        return
    slot = pending[0]
    inputs[slot.key] = slot.default
    await state.update_data(inputs=inputs)
    await _ask_next(cb.message, state)
    await cb.answer()


@router.message(GenFlow.fields)
async def got_field(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    spec = await _spec(data)
    inputs = data.get("inputs", {})
    pending = [s for s in spec.asked_slots() if s.key not in inputs]
    if not pending:
        return

    slot = pending[0]
    try:
        value = validate(slot.validator, message.text or "")
    except ValidationError as exc:
        await message.answer(INVALID_INPUT.format(reason=exc))
        return

    inputs[slot.key] = value
    await state.update_data(inputs=inputs)
    await _ask_next(message, state, edit=False)


async def _show_confirm(message: Message, state: FSMContext, edit: bool = True) -> None:
    data = await state.get_data()
    spec = await _spec(data)
    values = build_values(data["inputs"])
    await state.update_data(values=values)
    await state.set_state(GenFlow.confirming)

    text = CONFIRM
    kb = confirm_card(spec, values)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(GenFlow.confirming, F.data == "gen:render")
async def do_render(cb: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    user_id = cb.from_user.id

    if not await acquire_user_lock(user_id):
        await cb.answer("Still working on your last one…")
        return

    ref = f"render:{user_id}:{uuid.uuid4().hex[:12]}"
    kind = await credits.charge(user_id, settings.render_cost, ref)
    if kind is None:
        await release_user_lock(user_id)
        await cb.message.edit_text(NO_CREDITS)
        await cb.answer()
        return

    await state.set_state(GenFlow.rendering)
    await cb.message.edit_text(RENDERING)
    await cb.answer()

    started = time.perf_counter()
    spec = await _spec(data)
    values = data["values"]
    photo = data.get("photo")

    async with session_scope() as s:
        row = Render(user_id=user_id, template_id=spec.id, values=values, status="pending")
        s.add(row)
        await s.flush()
        render_id = row.id

    out = settings.render_path / str(user_id) / f"{render_id}.jpg"
    photos = {"photo": photo, "ghost": photo} if photo is not None else {}

    try:
        async with _sem:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, render, spec, values, out, photos, "card")
    except Exception as exc:  # noqa: BLE001
        await credits.refund(user_id, settings.render_cost, ref, kind)
        await release_user_lock(user_id)
        async with session_scope() as s:
            row = await s.get(Render, render_id)
            row.status = "failed"
            row.error = str(exc)
        await bot.send_message(user_id, RENDER_FAILED)
        return

    sent = await bot.send_photo(user_id, out.open("rb"), caption=RENDER_DONE,
                                reply_markup=result_actions(render_id))

    async with session_scope() as s:
        row = await s.get(Render, render_id)
        row.status = "done"
        row.path = str(out)
        row.file_id = sent.photo[-1].file_id
        row.duration_ms = int((time.perf_counter() - started) * 1000)

    await release_user_lock(user_id)
    await state.clear()
