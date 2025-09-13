from celery import Celery
from datetime import datetime
import os
import random
import json

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
AVAILABILITY_PERCENT = round(float(os.getenv("AVAILABILITY_PERCENT", "90")), 2)

celery = Celery(__name__, broker=CELERY_BROKER)
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@celery.task(name="order_status_request", queue="orders")
def order_status_request():
    now = datetime.now().isoformat()
    roll = random.randint(1, 100)
    available = roll <= AVAILABILITY_PERCENT
    result = {
        "component": "order_manager",
        "timestamp": now,
        "available": available,
        "roll": roll,
        "availability_percent": AVAILABILITY_PERCENT
    }
    print(f"[{now}] OrderManager: processed request -> {result}, forwarding to platform queue")
    celery.send_task("platform_callback", args=[json.dumps(result)], queue="platform")

    return result
