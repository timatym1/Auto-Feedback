from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from loguru import logger

from config.settings import settings
from database.session import engine
from database.unit_of_work import UnitOfWork
from handlers import client, creator
from middlewares.error_handler import GlobalErrorHandlerMiddleware
from middlewares.throttling import ThrottlingMiddleware
from schemas.dto import ScheduleFeedbackRequest, ScheduleFeedbackResponse, RFC7807Error
from services.client_service import ClientService
from services.feedback_service import FeedbackService
from services.taskiq_broker import broker
from services.tasks import send_nps_survey_task
from services.tenant_service import TenantService

# Aiogram setup
bot = Bot(token=settings.BOT_TOKEN.get_secret_value())
dp = Dispatcher()

# Register Middlewares & Handlers
dp.update.outer_middleware(GlobalErrorHandlerMiddleware())
dp.message.middleware(ThrottlingMiddleware(rate_limit=1.0))
dp.include_router(client.router)
dp.include_router(creator.router)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup & Shutdown lifecycle hook."""
    logger.info("Запуск приложения AutoFeedback & NPS Engine...")
    
    # TaskIQ broker initialization
    if not broker.is_worker_process:
        await broker.startup()

    # Startup notify CREATOR_ID
    if settings.CREATOR_ID:
        try:
            await bot.send_message(
                chat_id=settings.CREATOR_ID,
                text="🚀 **AutoFeedback Engine успешно запущен!**",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление о запуске CREATOR_ID: {e}")

    # Webhook setup if enabled
    if settings.USE_WEBHOOK and settings.WEBHOOK_HOST:
        webhook_url = f"{settings.WEBHOOK_HOST}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(
            url=webhook_url,
            secret_token=settings.WEBHOOK_SECRET.get_secret_value(),
            drop_pending_updates=True,
        )
        logger.info(f"Telegram Webhook установлен: {webhook_url}")

    yield

    # Graceful Shutdown
    logger.info("Остановка приложения AutoFeedback Engine...")
    if settings.USE_WEBHOOK:
        await bot.delete_webhook()

    if settings.CREATOR_ID:
        try:
            await bot.send_message(
                chat_id=settings.CREATOR_ID,
                text="🛑 **AutoFeedback Engine остановлен!**",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление об останове CREATOR_ID: {e}")

    await bot.session.close()
    if not broker.is_worker_process:
        await broker.shutdown()
    await engine.dispose()
    logger.info("Ресурсы БД и Redis успешно закрыты.")


app = FastAPI(
    title="AutoFeedback & NPS Engine API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# --- RFC 7807 Error Handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Глобальная обработка исключений в формате RFC 7807."""
    logger.exception(f"Unhandled REST Exception: {exc}")
    error_payload = RFC7807Error(
        type="https://errors.autofeedback.io/internal-server-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=str(exc) if settings.DEBUG else "Произошла внутренняя ошибка сервера.",
        instance=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump(),
    )


# --- REST Endpoints ---
@app.get("/health", tags=["Monitoring"])
async def health_check() -> dict:
    """Health check endpoint для Docker & K8s probes."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post(
    "/api/v1/feedback/schedule",
    response_model=ScheduleFeedbackResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Feedback Trigger"],
)
async def schedule_feedback(payload: ScheduleFeedbackRequest) -> ScheduleFeedbackResponse:
    """
    US-01: Планирование триггера опроса NPS из CRM с задержкой (Default: 120 мин).
    """
    async with UnitOfWork() as uow:
        tenant_service = TenantService(uow.session)
        client_service = ClientService(uow.session)
        feedback_service = FeedbackService(uow.session)

        # 1. Проверка существования тенанта и активности подписки
        tenant = await tenant_service.get_by_id(payload.tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Тенант с ID '{payload.tenant_id}' не найден.",
            )

        if not await tenant_service.is_subscription_active(tenant):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SUBSCRIPTION_INACTIVE: Подписка тенанта неактивна или истекла.",
            )

        # 2. Атомарный поиск/создание клиента
        client = await client_service.get_or_create_client(
            tenant_id=tenant.id,
            tg_user_id=payload.tg_user_id,
            phone_number=payload.client_phone,
        )

        # 3. Расчет времени отправки и запись в БД
        scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=payload.delay_minutes)
        report = await feedback_service.create_pending_report(
            tenant_id=tenant.id,
            client_id=client.id,
            scheduled_at=scheduled_at,
        )
        await uow.commit()

        # 4. Постановка задачи в брокер TaskIQ с отложенным вызовом
        task = await send_nps_survey_task.kiq(str(report.id))

        return ScheduleFeedbackResponse(
            status="success",
            task_id=str(task.task_id),
            scheduled_at=scheduled_at,
        )


@app.post(settings.WEBHOOK_PATH, include_in_schema=False)
async def telegram_webhook(request: Request) -> JSONResponse:
    """Прием обновлений бота через Webhook (от Aiogram)."""
    if not settings.USE_WEBHOOK:
        return JSONResponse(status_code=400, content={"message": "Webhook mode disabled"})

    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.WEBHOOK_SECRET.get_secret_value():
        return JSONResponse(status_code=403, content={"message": "Invalid secret token"})

    update_data = await request.json()
    update = Update.model_validate(update_data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return JSONResponse(status_code=200, content={"status": "ok"})