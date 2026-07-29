import traceback
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject
from loguru import logger

from config.settings import settings


class GlobalErrorHandlerMiddleware(BaseMiddleware):
    """
    Глобальный перехватчик ошибок:
    Логирует полный стек-трейс и отправляет критические ошибки Создателю системы.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as exc:
            tb = traceback.format_exc()
            logger.critical(f"Unhandled exception caught in handler: {exc}\n{tb}")

            bot: Bot = data.get("bot")
            if bot and settings.CREATOR_ID:
                alert_text = (
                    f"🚨 **CRITICAL BOT ERROR**\n\n"
                    f"**Exception:** `{type(exc).__name__}: {exc}`\n\n"
                    f"**Traceback:**\n```{tb[-1000:]}```"
                )
                try:
                    await bot.send_message(
                        chat_id=settings.CREATOR_ID,
                        text=alert_text,
                        parse_mode="Markdown",
                    )
                except Exception as alert_err:
                    logger.error(f"Failed to send alert to CREATOR_ID: {alert_err}")

            raise exc