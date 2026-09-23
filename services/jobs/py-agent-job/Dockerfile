FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY packages/infra /code/packages/infra
COPY packages/config /code/packages/config
COPY services/jobs/py-agent-job/pyproject.toml services/jobs/py-agent-job/uv.lock /code/services/jobs/py-agent-job/

RUN --mount=type=cache,target=/root/.cache/uv \
    cd services/jobs/py-agent-job \
    && uv sync --frozen --no-dev --no-install-project

COPY services/jobs/py-agent-job/src /code/services/jobs/py-agent-job/src

ENV PATH="/code/services/jobs/py-agent-job/.venv/bin:$PATH"

WORKDIR /code/services/jobs/py-agent-job/src

CMD ["python", "main.py"]