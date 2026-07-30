from taskiq import AsyncBroker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from config.settings import settings

result_backend = RedisAsyncResultBackend(redis_url=settings.redis_url)

broker: AsyncBroker = RedisStreamBroker(
    url=settings.redis_url,
).with_result_backend(result_backend)

# NOTE: Pydantic-схемы (ScheduleFeedbackRequest/Response, RFC7807Error,
# TenantCreateDTO/ReadDTO) удалены как дубликат schemas/dto.py.
# Использовать импорт из schemas.dto — единый источник истины.
