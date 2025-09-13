FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install --upgrade pip
RUN pip3 install -r /app/requirements.txt

COPY monitor/ /app/

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000"]
