# filepath: services/nps_service.py
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from database.models import FeedbackRequest, RequestStatus, Tenant, Customer, Incident, IncidentStatus
from keyboards.nps_keyboards import get_nps_keyboard
from utils.logger import logger
from utils.redis_client import redis_client
from services.task_broker import broker

@broker.task
async def send_nps_request_task(request_id_str: str) -> None:
    from database.db import AsyncSessionLocal
    from config.config import settings

    request_id = uuid.UUID(request_id_str)
    bot = Bot(token=settings.BOT_TOKEN)

    async with AsyncSessionLocal() as session:
        stmt = (
            select(FeedbackRequest)
            .where(FeedbackRequest.id == request_id)
            .execution_options(populate_existing=True)
        )
        res = await session.execute(stmt)
        req = res.scalar_one_or_none()

        if not req or req.status != RequestStatus.SCHEDULED:
            logger.warning(f"Запрос {request_id} не найден или уже обработан.")
            await bot.session.close()
            return

        stmt_cust = select(Customer).where(Customer.id == req.customer_id)
        cust_res = await session.execute(stmt_cust)
        customer = cust_res.scalar_one_or_none()

        stmt_tenant = select(Tenant).where(Tenant.id == req.tenant_id)
        tenant_res = await session.execute(stmt_tenant)
        tenant = tenant_res.scalar_one_or_none()

        if not customer or not customer.telegram_id:
            logger.error(f"У клиента для запроса {request_id} отсутствует telegram_id.")
            req.status = RequestStatus.FAILED
            await session.commit()
            await bot.session.close()
            return

        try:
            message_text = (
                f"Здравствуйте! Спасибо за посещение **{tenant.company_name}**.\n\n"
                f"Пожалуйста, оцените качество нашего обслуживания от 1 до 5 звезд:"
            )
            await bot.send_message(
                chat_id=int(customer.telegram_id),
                text=message_text,
                reply_markup=get_nps_keyboard(str(req.id)),
                parse_mode="Markdown"
            )
            req.status = RequestStatus.SENT
            req.sent_at = datetime.now(timezone.utc)
            await session.commit()
            logger.info(f"NPS опрос по запросу {request_id} успешно отправлен.")
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.error(f"Ошибка отправки бота пользователю {customer.telegram_id}: {e}")
            req.status = RequestStatus.FAILED
            await session.commit()
        except Exception as e:
            logger.exception(f"Непредвиденная ошибка при отправке запроса {request_id}: {e}")
            req.status = RequestStatus.FAILED
            await session.commit()
        finally:
            await bot.session.close()


class NPSService:
    @staticmethod
    async def process_rating(
        session: AsyncSession,
        request_id: uuid.UUID,
        rating: int,
        telegram_id: str
    ) -> tuple[bool, str, Optional[Tenant]]:
        """Обработка нажатия на оценку с идемпотентностью через Redis Lock."""
        lock_key = f"feedback_lock:{request_id}"
        acquired = await redis_client.set(lock_key, "locked", nx=True, ex=60)
        
        if not acquired:
            return False, "Оценка по данному запросу уже принята или обрабатывается.", None

        stmt = select(FeedbackRequest).where(FeedbackRequest.id == request_id)
        res = await session.execute(stmt)
        req = res.scalar_one_or_none()

        if not req:
            return False, "Запрос оценки не найден.", None

        if req.status == RequestStatus.COMPLETED:
            return False, "Вы уже оставили отзыв по данному посещению.", None

        req.rating = rating
        req.status = RequestStatus.COMPLETED
        
        stmt_tenant = select(Tenant).where(Tenant.id == req.tenant_id)
        tenant_res = await session.execute(stmt_tenant)
        tenant = tenant_res.scalar_one_or_none()

        if rating <= 3:
            incident = Incident(
                request_id=req.id,
                resolution_status=IncidentStatus.OPEN
            )
            session.add(incident)

        await session.commit()
        return True, "Success", tenant

    @staticmethod
    async def save_incident_comment(
        session: AsyncSession,
        request_id: uuid.UUID,
        comment: str
    ) -> Optional[Incident]:
        stmt = select(Incident).where(Incident.request_id == request_id)
        res = await session.execute(stmt)
        incident = res.scalar_one_or_none()

        if incident:
            incident.customer_comment = comment
            await session.commit()
            await session.refresh(incident)
        return incident