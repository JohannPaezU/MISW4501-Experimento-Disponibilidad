FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY order_manager/ /app/

CMD ["celery", "-A", "app.celery", "worker", "--loglevel=info", "-Q", "orders"]
