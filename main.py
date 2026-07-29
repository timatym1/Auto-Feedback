# filepath: main.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from aiogram import Bot, Dispatcher

from config.config import settings
from database.db import engine, Base
from handlers.api_routes import router as api_router
from handlers.nps_handlers import router as bot_router
from services.task_broker import broker
from utils.logger import logger

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
dp.include_router(bot_router)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт приложения
    logger.info("Инициализация базы данных...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Запуск Taskiq Broker...")
    await broker.startup()

    asyncio.create_task(dp.start_polling(bot))
    logger.info("Telegram Bot Polling запущен.")

    yield

    # Завершение работы приложения
    logger.info("Остановка приложений...")
    await dp.stop_polling()
    await bot.session.close()
    await broker.shutdown()
    await engine.dispose()
    logger.info("Приложение полностью остановлено.")

app = FastAPI(
    title="AutoFeedback & NPS Engine API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)