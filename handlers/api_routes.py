# filepath: handlers/api_routes.py
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.db import get_db_session
from database.models import Tenant, Customer, FeedbackRequest, RequestStatus
from services.nps_service import send_nps_request_task
from utils.logger import logger

router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])

class ScheduleFeedbackSchema(BaseModel):
    tenant_id: uuid.UUID
    customer_phone: str = Field(..., example="+77015550199")
    customer_telegram_id: str = Field(..., example="384920182")
    delay_minutes: int = Field(default=120, ge=0)

class ScheduleFeedbackResponse(BaseModel):
    status: str
    request_id: uuid.UUID
    scheduled_at: datetime

@router.post("/schedule", response_model=ScheduleFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def schedule_feedback(
    payload: ScheduleFeedbackSchema,
    session: AsyncSession = Depends(get_db_session)
):
    stmt_tenant = select(Tenant).where(Tenant.id == payload.tenant_id)
    res_tenant = await session.execute(stmt_tenant)
    tenant = res_tenant.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="Тенант не найден.")

    stmt_cust = select(Customer).where(
        Customer.tenant_id == payload.tenant_id,
        Customer.phone_number == payload.customer_phone
    )
    res_cust = await session.execute(stmt_cust)
    customer = res_cust.scalar_one_or_none()

    if not customer:
        customer = Customer(
            tenant_id=payload.tenant_id,
            phone_number=payload.customer_phone,
            telegram_id=payload.customer_telegram_id
        )
        session.add(customer)
        await session.flush()
    else:
        if payload.customer_telegram_id and customer.telegram_id != payload.customer_telegram_id:
            customer.telegram_id = payload.customer_telegram_id

    scheduled_time = datetime.now(timezone.utc) + timedelta(minutes=payload.delay_minutes)
    
    feedback_request = FeedbackRequest(
        tenant_id=payload.tenant_id,
        customer_id=customer.id,
        status=RequestStatus.SCHEDULED,
        scheduled_at=scheduled_time
    )
    session.add(feedback_request)
    await session.commit()
    await session.refresh(feedback_request)

    # Постановка задачи в очередь с задержкой 120 минут
    try:
        await send_nps_request_task.schedule_by_time(
            source=scheduled_time,
            request_id_str=str(feedback_request.id)
        )
        logger.info(f"Запрос {feedback_request.id} успешно запланирован на {scheduled_time}")
    except Exception as e:
        logger.exception(f"Ошибка планирования задачи в Taskiq: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при создании фоновой задачи.")

    return ScheduleFeedbackResponse(
        status="SUCCESS",
        request_id=feedback_request.id,
        scheduled_at=scheduled_time
    )