from fastapi import FastAPI, status, APIRouter, Response
from celery import Celery
from datetime import datetime
import os
import json
import redis

app = FastAPI(title="Monitor API", version=os.getenv("VERSION", "1.0"))
router = APIRouter(prefix="/monitor")

CELERY_BROKER = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
EXPECTED_AVAILABILITY = round(float(os.getenv("EXPECTED_AVAILABILITY", "90")), 2)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

celery = Celery(__name__, broker=CELERY_BROKER)
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.get("/orders/status/check", status_code=status.HTTP_200_OK)
def enqueue_status_check():
    print(f"[{datetime.now()}] Monitor: enqueueing platform_request")
    celery.send_task("platform_request", queue="platform")

    return {"status": "Request enqueued"}


@router.get("/orders/status", status_code=status.HTTP_200_OK)
def get_orders_status(response: Response):
    try:
        orders_availability = _get_order_availability()
        total_records = len(orders_availability)
        if total_records == 0:
            response_data = {
                "total_records": 0,
                "real_availability_percentage": 0.0,
                "expected_availability_percentage": EXPECTED_AVAILABILITY,
                "orders_availability": []
            }
            return response_data

        available_orders = sum(1 for order in orders_availability if order.get("available", False))
        real_availability_percentage = (available_orders / total_records) * 100
        
        response_data = {
            "total_records": total_records,
            "real_availability_percentage": round(real_availability_percentage, 2),
            "expected_availability_percentage": EXPECTED_AVAILABILITY,
            "orders_availability": orders_availability
        }

        if real_availability_percentage < EXPECTED_AVAILABILITY:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return response_data
        
    except Exception as e:
        print(f"An unexpected error has occurred, details: {e}")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"orders_availability": [], "error": f"{e}"}


@router.post("/orders/status/reset", status_code=status.HTTP_200_OK)
def reset_orders_status():
    try:
        availability_keys = redis_client.keys("availability:*")
        for key in availability_keys:
            redis_client.delete(key)

        return {"status": "All availability records have been deleted"}
    except Exception as e:
        print(f"An unexpected error has occurred, details: {e}")
        return {"status": "Error", "error": f"{e}"}


def _get_order_availability():
    try:
        availability_keys = redis_client.keys("availability:*")
        orders_availability = []
        for key in sorted(availability_keys):
            data_str = redis_client.get(key)
            if data_str:
                data = json.loads(data_str)
                orders_availability.append(data)

        return orders_availability
    except Exception as e:
        print(f"An unexpected error has occurred, details: {e}")
        return []


@celery.task(name="monitor_callback", queue="monitor")
def monitor_callback(response):
    try:
        data = response if isinstance(response, dict) else json.loads(response)
    except Exception:
        data = {"info": str(response)}

    print(f"[{datetime.now()}] Monitor: CALLBACK received -> {data}")

    try:
        timestamp = data.get('timestamp', datetime.now().isoformat())
        redis_key = f"availability:{timestamp}"
        redis_client.set(redis_key, json.dumps(data))
        print(f"[{datetime.now()}] Monitor: Data saved to Redis with key {redis_key}")
    except Exception as e:
        print(f"[{datetime.now()}] Monitor: Error saving to Redis: {e}")

    return data


app.include_router(router)
