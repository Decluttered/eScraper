import os

from dramatiq.brokers.redis import RedisBroker

from app.core.config import get_settings

settings = get_settings()
broker = RedisBroker(url=settings.redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
dramatiq.set_broker(broker)
