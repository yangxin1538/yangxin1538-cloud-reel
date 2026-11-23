FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8088 \
    SOURCE_ROOT=/CloudNAS \
    STRM_ROOT=/strm/CloudReel \
    STRM_MODE=file \
    SCAN_INTERVAL_MINUTES=60 \
    DATA_DIR=/app/data \
    CONFIG_DIR=/app/config

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY web ./web

EXPOSE 8088
CMD ["python", "-m", "app.main"]
