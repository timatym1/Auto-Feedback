# filepath: services/task_broker.py
from taskiq_redis import ListQueueBroker
from config.config import settings

broker = ListQueueBroker(url=settings.REDIS_URL)