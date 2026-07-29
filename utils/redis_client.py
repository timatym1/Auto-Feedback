# filepath: utils/redis_client.py
from redis.asyncio import Redis
from config.config import settings

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)