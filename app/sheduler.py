import logging

from apscheduler import events
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Добавил логирование для проверки выполнения задач
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

scheduler.add_listener(
    lambda event: logger.info(f"Событие: {event}"),
    events.EVENT_ALL
)

scheduler.start()
