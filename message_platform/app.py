from celery import Celery
from datetime import datetime
import os

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
celery = Celery(__name__, broker=CELERY_BROKER)
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery.task(name="platform_request", queue="platform")
def platform_request():
    print(f"[{datetime.now()}] MessagePlatform: received platform_request -> forwarding to orders queue")
    celery.send_task("order_status_request", queue="orders")

    return {"status": "forwarded to orders queue"}


@celery.task(name="platform_callback", queue="platform")
def platform_callback(response):
    print(f"[{datetime.now()}] MessagePlatform: platform_callback -> {response}, forwarding to monitor queue")
    celery.send_task("monitor_callback", args=[response], queue="monitor")

    return response
