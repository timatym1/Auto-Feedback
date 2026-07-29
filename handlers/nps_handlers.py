# filepath: handlers/nps_handlers.py
import uuid
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.db import AsyncSessionLocal
from database.models import Tenant
from keyboards.nps_keyboards import get_maps_keyboard
from services.nps_service import NPSService
from states.feedback_states import FeedbackFSM
from utils.logger import logger

router = Router()

@router.callback_query(F.data.startswith("nps:"))
async def handle_nps_rating(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    request_id = uuid.UUID(parts[1])
    rating = int(parts[2])
    telegram_id = str(callback.from_user.id)

    async with AsyncSessionLocal() as session:
        success, message, tenant = await NPSService.process_rating(
            session=session,
            request_id=request_id,
            rating=rating,
            telegram_id=telegram_id
        )

    if not success:
        await callback.answer(message, show_alert=True)
        return

    await callback.answer()

    if rating >= 4:
        promo_code = f"PROMO10-{telegram_id[-4:]}"
        text = (
            f"Спасибо за высокую оценку! 🎉\n\n"
            f"Мы будем очень благодарны, если вы продублируете ваш отзыв на картах.\n"
            f"Ваш промокод на скидку 10%: `{promo_code}`"
        )
        markup = get_maps_keyboard(tenant.map_link_2gis, tenant.map_link_google) if tenant else None
        await callback.message.edit_text(text=text, reply_markup=markup, parse_mode="Markdown")
    else:
        await state.update_data(request_id=str(request_id), tenant_admin_id=tenant.admin_telegram_id if tenant else None)
        await state.set_state(FeedbackFSM.waiting_for_negative_comment)
        await callback.message.edit_text(
            text="Нам очень жаль, что ваше посещение прошло неидеально. 😔\n"
                 "Пожалуйста, напишите, что именно вам не понравилось? Руководство лично прочитает ваше сообщение."
        )

@router.message(FeedbackFSM.waiting_for_negative_comment)
async def handle_negative_comment(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    request_id_str = data.get("request_id")
    tenant_admin_id = data.get("tenant_admin_id")

    if not request_id_str:
        await state.clear()
        return

    comment_text = message.text or message.caption or "[Голосовое сообщение / Медиа]"
    request_id = uuid.UUID(request_id_str)

    async with AsyncSessionLocal() as session:
        await NPSService.save_incident_comment(
            session=session,
            request_id=request_id,
            comment=comment_text
        )

    await message.answer("Спасибо за обратную связь! Мы уже передали информацию руководству для решения проблемы.")

    if tenant_admin_id:
        try:
            alert_text = (
                f"🚨 **НЕГАТИВНЫЙ ОТЗЫВ**\n\n"
                f"**От пользователя:** @{message.from_user.username or 'без_юзернейма'} (ID: `{message.from_user.id}`)\n"
                f"**Комментарий:**\n{comment_text}"
            )
            await bot.send_message(chat_id=int(tenant_admin_id), text=alert_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление администратору {tenant_admin_id}: {e}")

    await state.clear()