from aiogram.fsm.state import State, StatesGroup


class FeedbackSG(StatesGroup):
    waiting_for_negative_reason = State()


class TenantSetupSG(StatesGroup):
    waiting_for_company_name = State()
    waiting_for_director_tg_id = State()
    waiting_for_2gis_link = State()
    waiting_for_google_link = State()