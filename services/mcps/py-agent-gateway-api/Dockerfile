FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY packages/config /code/packages/config

COPY services/mcps/py-agent-gateway-api/pyproject.toml services/mcps/py-agent-gateway-api/uv.lock /code/services/mcps/py-agent-gateway-api/

RUN --mount=type=cache,target=/root/.cache/uv \
    cd services/mcps/py-agent-gateway-api \
    && uv sync --frozen --no-dev --no-install-project

COPY services/mcps/py-agent-gateway-api/src /code/services/mcps/py-agent-gateway-api/src

ENV PATH="/code/services/mcps/py-agent-gateway-api/.venv/bin:$PATH"

WORKDIR /code/services/mcps/py-agent-gateway-api/src

EXPOSE 8000

CMD ["python", "main.py"]