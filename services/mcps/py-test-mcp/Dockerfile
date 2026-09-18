FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY services/mcps/py-test-mcp/pyproject.toml services/mcps/py-test-mcp/uv.lock /code/services/mcps/py-test-mcp/

RUN --mount=type=cache,target=/root/.cache/uv \
    cd services/mcps/py-test-mcp \
    && uv sync --frozen --no-dev --no-install-project

COPY services/mcps/py-test-mcp/src /code/services/mcps/py-test-mcp/src

ENV PATH="/code/services/mcps/py-test-mcp/.venv/bin:$PATH"

WORKDIR /code/services/mcps/py-test-mcp/src

CMD ["python", "main.py"]