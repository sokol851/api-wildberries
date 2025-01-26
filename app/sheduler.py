import logging

from apscheduler import events
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from decouple import config
from sqlalchemy import create_engine

# Добавил логирование для проверки выполнения задач
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

user = config('POSTGRES_USER')
password = config('POSTGRES_PASSWORD')
host = config('POSTGRES_HOST')
port = config('POSTGRES_PORT')
dbname = config('POSTGRES_DB')

# Синхронный URL для SQLAlchemyJobStore
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

engine = create_engine(DATABASE_URL)

# Настройка хранилища задач
job_stores = {
    'default': SQLAlchemyJobStore(engine=engine)
}

# Инициализация планировщика с использованием хранилища задач
scheduler = AsyncIOScheduler(jobstores=job_stores)

scheduler.add_listener(
    lambda event: logger.info(f"Событие: {event}"),
    events.EVENT_ALL
)

scheduler.start()
