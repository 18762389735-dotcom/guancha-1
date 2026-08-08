FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY . .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir "./backend[openai]"

EXPOSE 8080

CMD ["sh", "-c", "uvicorn guancha_api.main:app --app-dir backend/src --host 0.0.0.0 --port ${PORT:-8080}"]
