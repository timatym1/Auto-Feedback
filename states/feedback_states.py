# filepath: states/feedback_states.py
from aiogram.fsm.state import State, StatesGroup

class FeedbackFSM(StatesGroup):
    waiting_for_negative_comment = State()