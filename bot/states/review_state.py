from aiogram.fsm.state import State, StatesGroup


class ReviewFSM(StatesGroup):
    waiting_rating = State()
    waiting_text = State()
