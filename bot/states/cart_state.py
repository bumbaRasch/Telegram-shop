from aiogram.fsm.state import State, StatesGroup


class CartStates(StatesGroup):
    viewing_cart = State()
