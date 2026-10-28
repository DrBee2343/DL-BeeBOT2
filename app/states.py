from aiogram.fsm.state import State, StatesGroup


class GenFlow(StatesGroup):
    picking = State()
    photo = State()
    background = State()
    fields = State()
    confirming = State()
    rendering = State()


class EditFlow(StatesGroup):
    picking = State()
    value = State()


class Billing(StatesGroup):
    picking = State()
    awaiting_crypto = State()


class AdminFlow(StatesGroup):
    user_lookup = State()
    grant = State()
