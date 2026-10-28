from aiogram.fsm.state import State, StatesGroup


class GenFlow(StatesGroup):
    browsing = State()
    collecting = State()
    confirming = State()
    rendering = State()


class EditFlow(StatesGroup):
    menu = State()
    awaiting_value = State()


class Billing(StatesGroup):
    choosing_plan = State()
    awaiting_proof = State()
