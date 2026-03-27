from aiogram.filters.state import State, StatesGroup


class UserMgmtStates(StatesGroup):
    """FSM for user management flow."""

    waiting_user_id_for_check = State()
    waiting_user_replenish = State()
    waiting_user_deduct = State()
