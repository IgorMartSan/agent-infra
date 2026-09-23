import os
from functools import lru_cache

from sqlalchemy import URL, Engine, create_engine


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"A variável {name} precisa ser configurada no .env.")
    return value


def build_database_url() -> URL:
    """Monta a URL sem concatenar ou expor usuário e senha."""
    return URL.create(
        drivername=os.getenv("SQL_DATABASE_DRIVER", "postgresql+psycopg"),
        username=_required_env("SQL_DATABASE_USER"),
        password=_required_env("SQL_DATABASE_PASSWORD"),
        host=_required_env("SQL_DATABASE_HOST"),
        port=int(os.getenv("SQL_DATABASE_PORT", "5432")),
        database=_required_env("SQL_DATABASE_NAME"),
        query={"sslmode": os.getenv("SQL_DATABASE_SSLMODE", "prefer")},
    )


@lru_cache(maxsize=1)
def get_database_engine() -> Engine:
    timeout_ms = int(os.getenv("SQL_QUERY_TIMEOUT_SECONDS", "30")) * 1000
    return create_engine(
        build_database_url(),
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        connect_args={
            "options": f"-c default_transaction_read_only=on -c statement_timeout={timeout_ms}"
        },
    )
