from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import escape_md
from loguru import logger

from config.settings import settings
from database.unit_of_work import UnitOfWork
from services.client_service import ClientService
from services.feedback_service import FeedbackService
from services.taskiq_broker import broker
from services.tenant_service import TenantService


def get_nps_keyboard(report_id: UUID) -> InlineKeyboardMarkup:
    """Генерация клавиатуры с кнопками оценки от 1 до 5."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"⭐ {i}", callback_data=f"nps_score:{report_id}:{i}"
            )
            for i in range(1, 6)
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@broker.task(task_name="send_nps_survey_task")
async def send_nps_survey_task(report_id_str: str) -> None:
    """
    Фоновая задача TaskIQ:
    1. Проверяет активность подписки тенанта на момент отправки.
    2. Отправляет клиенту опрос в Telegram.
    3. Обрабатывает исключения (например, BOT_BLOCKED_BY_USER).
    """
    report_id = UUID(report_id_str)
    logger.info(f"Запуск фоновой задачи отправки NPS отчета: {report_id}")

    bot = Bot(token=settings.BOT_TOKEN.get_secret_value())

    try:
        async with UnitOfWork() as uow:
            feedback_service = FeedbackService(uow.session)
            tenant_service = TenantService(uow.session)
            client_service = ClientService(uow.session)

            report = await feedback_service.get_by_id(report_id)
            if not report:
                logger.error(f"Отчет {report_id} не найден в БД.")
                return

            tenant = await tenant_service.get_by_id(report.tenant_id)
            if not tenant:
                logger.error(f"Тенант {report.tenant_id} не найден.")
                await feedback_service.mark_as_failed(report_id)
                await uow.commit()
                return

            # Выполнение Edge Case NFR: проверка подписки прямо перед отправкой
            if not await tenant_service.is_subscription_active(tenant):
                logger.warning(
                    f"Подписка тенанта {tenant.company_name} неактивна. Запрос {report_id} отменен (SUBSCRIPTION_INACTIVE)."
                )
                await feedback_service.mark_as_failed(report_id)
                await uow.commit()
                return

            client = report.client
            keyboard = get_nps_keyboard(report.id)

            safe_company_name = escape_md(tenant.company_name)  # FIX: escape для Markdown parse_mode
            message_text = (
                f"Здравствуйте! 👋\n\n"
                f"Благодарим вас за посещение **{safe_company_name}**!\n"
                f"Пожалуйста, оцените качество нашего обслуживания от 1 до 5 stars:"
            )

            try:
                await bot.send_message(
                    chat_id=int(client.tg_user_id),
                    text=message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                await feedback_service.mark_as_sent(report_id)
                await uow.commit()
                logger.info(f"NPS опрос успешно отправлен клиенту {client.tg_user_id}")

            except TelegramRetryAfter as flood_err:
                # FIX: rate-limit — это retryable, не считаем провалом отправки
                logger.warning(
                    f"Flood control при отправке {client.tg_user_id}: retry_after={flood_err.retry_after}s"
                )
                await uow.rollback()
                raise  # пусть TaskIQ ретраит задачу согласно своей retry-политике

            except TelegramForbiddenError:
                # FIX: клиент реально заблокировал бота — единственный настоящий BOT_BLOCKED_BY_USER
                logger.warning(f"Клиент {client.tg_user_id} заблокировал бота [BOT_BLOCKED_BY_USER]")
                await feedback_service.mark_as_failed(report_id)
                await uow.commit()

            except TelegramBadRequest as bad_req:
                # FIX: например, невалидная разметка/chat_id — не ретраим бесконечно
                logger.error(f"Bad request при отправке {client.tg_user_id}: {bad_req}")
                await feedback_service.mark_as_failed(report_id)
                await uow.commit()

    finally:
        await bot.session.close()