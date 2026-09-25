"""Infraestrutura de conexão PostgreSQL (SQLAlchemy async).

Cópia adaptada de services/apis/py-agent-gateway-api/src/infra/postgresql/connection.py.
Diferença: monta a DATABASE_URL a partir das variáveis separadas do .env
(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD) em vez de exigir
DATABASE_URL pronta. Mantém o mesmo padrão de engine + session_factory
usado no restante do projeto.
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()


def _build_database_url() -> URL:
    """Monta a URL de conexão para asyncpg a partir das variáveis do .env."""
    host = os.getenv('DB_HOST', '127.0.0.1')
    port = os.getenv('DB_PORT', '5432')
    name = os.getenv('DB_NAME') or os.getenv('DB_DATABASE', 'rsa')
    user = os.getenv('DB_USER') or os.getenv('DB_USERNAME', 'rsa')
    password = os.getenv('DB_PASSWORD', 'rsa')
    # asyncpg usa o driver postgresql+asyncpg
    return URL.create(
        'postgresql+asyncpg', username=user, password=password,
        host=host, port=int(port), database=name,
    )


DATABASE_URL = _build_database_url()

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield uma sessão async do SQLAlchemy (uso típico em dependências)."""
    async with session_factory() as session:
        yield session


async def close_database() -> None:
    """Descarta o pool de conexões (chamar no shutdown do servidor)."""
    await engine.dispose()
