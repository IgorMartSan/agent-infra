FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY packages/infra /code/packages/infra
COPY packages/config /code/packages/config
COPY services/jobs/py-agent-job/pyproject.toml services/jobs/py-agent-job/uv.lock /code/services/jobs/py-agent-job/
COPY services/mcps/py-mcp-rsa/pyproject.toml services/mcps/py-mcp-rsa/uv.lock /code/services/mcps/py-mcp-rsa/

RUN --mount=type=cache,target=/root/.cache/uv \
    cd services/jobs/py-agent-job \
    && uv sync --frozen --no-dev --no-install-project \
    && cd /code/services/mcps/py-mcp-rsa \
    && uv sync --frozen --no-dev --no-install-project

COPY services/jobs/py-agent-job/src /code/services/jobs/py-agent-job/src
COPY services/mcps/py-mcp-rsa/src /code/services/mcps/py-mcp-rsa/src
COPY services/mcps/py-mcp-rsa/.env /code/services/mcps/py-mcp-rsa/.env
RUN sed -i 's/^DB_HOST=.*/DB_HOST=host.docker.internal/' /code/services/mcps/py-mcp-rsa/.env

ENV PATH="/code/services/jobs/py-agent-job/.venv/bin:$PATH" \
    MCP_SERVER_PATH="/code/services/mcps/py-mcp-rsa/src/main.py" \
    MCP_PYTHON_EXECUTABLE="/code/services/mcps/py-mcp-rsa/.venv/bin/python"

WORKDIR /code/services/jobs/py-agent-job/src

CMD ["python", "main.py"]
