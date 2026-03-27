from aiogram.filters.state import State, StatesGroup


class BalanceStates(StatesGroup):
    """FSM states for the balance top-up flow."""

    waiting_amount = State()
    waiting_payment = State()
