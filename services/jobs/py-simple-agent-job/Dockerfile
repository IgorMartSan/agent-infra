FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY packages/infra /code/packages/infra
COPY packages/config /code/packages/config

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir /code/packages/infra /code/packages/config \
    && pip install --no-cache-dir \
        "pika>=1.3.2" \
        "langgraph>=1.1.4,<2.0.0" \
        "python-dotenv>=1.2.2" \
        "redis>=5.0.0"

COPY services/jobs/py-simple-agent-job/src /code/services/jobs/py-simple-agent-job/src

WORKDIR /code/services/jobs/py-simple-agent-job/src

CMD ["python", "main.py"]
