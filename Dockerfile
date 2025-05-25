FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bluesky-webook-forwarder.py .

CMD ["python", "bluesky-webook-forwarder.py"]