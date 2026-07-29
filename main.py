import asyncio
import uvicorn
from loguru import logger
from config.settings import settings
from src.app import app, dp, bot


async def start_long_polling() -> None:
    """Запуск бота в режиме Long Polling (для локальной разработки/dev среды)."""
    logger.info("Запуск бота в режиме Long Polling...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    if settings.USE_WEBHOOK:
        # FastAPI Webhook Mode
        logger.info(f"Запуск FastAPI на {settings.APP_HOST}:{settings.APP_PORT}...")
        uvicorn.run(
            "src.app:app",
            host=settings.APP_HOST,
            port=settings.APP_PORT,
            reload=settings.DEBUG,
        )
    else:
        # Asyncio Long Polling Mode
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(start_long_polling())
        except (KeyboardInterrupt, SystemExit):
            logger.info("Long Polling остановлен.")