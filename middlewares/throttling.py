from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from redis.asyncio import Redis

from config.settings import settings


class ThrottlingMiddleware(BaseMiddleware):
    """Redis-based Rate Limiter для предотвращения спама в боте."""

    def __init__(self, rate_limit: float = 1.0) -> None:
        self.rate_limit = rate_limit
        self.redis = Redis.from_url(settings.redis_url)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        key = f"throttling:{user.id}"
        is_restricted = await self.redis.get(key)

        if is_restricted:
            # Превышен лимит запросов, игнорируем событие
            return None

        await self.redis.set(key, "1", px=int(self.rate_limit * 1000))
        return await handler(event, data)