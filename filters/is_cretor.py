from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config.settings import settings


class IsCreatorFilter(BaseFilter):
    """Фильтр проверки прав Создателя системы (SaaS Owner)."""

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id if event.from_user else 0
        return user_id == settings.CREATOR_ID