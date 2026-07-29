from uuid import UUID

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger

from database.unit_of_work import UnitOfWork
from keyboards.inline import get_high_score_keyboard
from services.feedback_service import FeedbackService
from services.tenant_service import TenantService
from states.feedback import FeedbackSG

router = Router(name="client_router")


@router.callback_query(F.data.startswith("nps_score:"))
async def process_nps_score(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    """Обработка выбора оценки от 1 до 5."""
    parts = callback.data.split(":")
    report_id = UUID(parts[1])
    score = int(parts[2])

    async with UnitOfWork() as uow:
        feedback_service = FeedbackService(uow.session)
        tenant_service = TenantService(uow.session)

        report = await feedback_service.record_score(report_id, score)
        if not report:
            await callback.answer("Ошибка: опрос не найден или устарел.", show_alert=True)
            return

        tenant = await tenant_service.get_by_id(report.tenant_id)
        await uow.commit()

        await callback.message.edit_reply_markup(reply_markup=None)

        if score >= 4:
            # High Score Flow (4-5): Отправляем ссылки на карты + промокод
            kb = get_high_score_keyboard(
                link_2gis=tenant.review_link_2gis if tenant else None,
                link_google=tenant.review_link_google if tenant else None,
            )
            text = (
                f"Спасибо за высокую оценку! 🌟\n\n"
                f"Мы будем очень благодарны, если вы продублируете свой отзыв "
                f"на картах. В знак признательности дарим вам скидку 10% на следующее посещение по промокоду **THANKYOU10**!"
            )
            await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
            await callback.answer()
        else:
            # Low Score Flow (1-3): Перехват негатива, просим описать проблему
            await state.update_data(report_id=str(report_id))
            await state.set_state(FeedbackSG.waiting_for_negative_reason)
            await callback.message.answer(
                "Нам очень жаль, что у вас осталось неприятное впечатление. 😔\n\n"
                "Пожалуйста, напишите, что именно вам не понравилось? "
                "Ваш отзыв напрямую получит директор компании."
            )
            await callback.answer()


@router.message(FeedbackSG.waiting_for_negative_reason)
async def process_negative_reason(message: Message, state: FSMContext, bot: Bot) -> None:
    """Обработка текста негативного отзыва и эскалация директору."""
    user_data = await state.get_data()
    report_id_str = user_data.get("report_id")

    if not report_id_str:
        await state.clear()
        return

    report_id = UUID(report_id_str)
    reason_text = message.text or message.caption or "[Голосовое/Медиа сообщение]"

    async with UnitOfWork() as uow:
        feedback_service = FeedbackService(uow.session)
        tenant_service = TenantService(uow.session)

        report = await feedback_service.record_negative_reason(report_id, reason_text)
        if not report:
            await message.answer("Ошибка сохранения отзыва.")
            await state.clear()
            return

        tenant = await tenant_service.get_by_id(report.tenant_id)
        client = report.client
        await uow.commit()

        # Эскалация: мгновенное уведомление директору бизнеса
        if tenant and tenant.director_tg_id:
            alert_text = (
                f"⚠️ **НОВЫЙ НЕГАТИВНЫЙ ОТЗЫВ!**\n\n"
                f"**Компания:** {tenant.company_name}\n"
                f"**Клиент TG ID:** `{client.tg_user_id}`\n"
                f"**Телефон:** {client.phone_number or 'Не указан'}\n"
                f"**Оценка:** {report.score} / 5 ⭐️\n\n"
                f"**Жалоба:**\n_{reason_text}_"
            )
            try:
                await bot.send_message(
                    chat_id=int(tenant.director_tg_id),
                    text=alert_text,
                    parse_mode="Markdown",
                )
                logger.info(f"Жалоба по отчету {report_id} успешно эскалирована директору {tenant.director_tg_id}")
            except Exception as err:
                logger.error(f"Не удалось отправить алерт директору {tenant.director_tg_id}: {err}")

    await state.clear()
    await message.answer("Спасибо за обратную связь! Передали информацию руководству для исправления ситуации. 🙏")