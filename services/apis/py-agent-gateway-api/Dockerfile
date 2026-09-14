FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY packages/config /code/packages/config

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /code/packages/config \
    && pip install --no-cache-dir \
        "asyncpg>=0.30.0" \
        "fastapi>=0.115.3" \
        "pika>=1.3.2" \
        "pydantic>=2.5.0" \
        "python-dotenv>=1.2.2" \
        "sqlalchemy>=2.0.49" \
        "uvicorn>=0.41.0"

COPY services/apis/py-agent-gateway-api/src /code/services/apis/py-agent-gateway-api/src

WORKDIR /code/services/apis/py-agent-gateway-api/src

EXPOSE 8000

CMD ["python", "main.py"]
