import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from langchain_community.utilities import SQLDatabase

logger = logging.getLogger(__name__)


class PostgresConnection:
    """
    Gerencia a conexão com o PostgreSQL.

    Responsável por:
    - Criar engine única
    - Validar conexão
    - Expor o engine e a fábrica de sessões

    NÃO deve conter lógica de negócio.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        user: str = "postgres",
        password: str = "postgres",
        database: str = "postgres",
    ):
        """Inicializa a configuração da conexão e abre a conexão com o banco."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

        self._connect()

    def _connect(self) -> None:
        """Inicializa a conexão com o PostgreSQL."""
        try:
            database_url = URL.create(
                drivername="postgresql+psycopg2",
                username=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
                database=self.database,
            )

            self._engine = create_engine(database_url)

            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            self._session_factory = sessionmaker(
                bind=self._engine,
                autoflush=False,
                autocommit=False,
            )

            logger.info("Conectado ao PostgreSQL com sucesso")

        except Exception:
            logger.exception("Erro ao conectar no PostgreSQL")
            raise

    def get_engine(self) -> Engine:
        """Retorna o engine ativo."""
        if self._engine is None:
            raise RuntimeError("PostgreSQL não está conectado")
        return self._engine

    def get_session(self) -> Session:
        """Retorna uma nova sessão ativa."""
        if self._session_factory is None:
            raise RuntimeError("PostgreSQL não está conectado")
        return self._session_factory()

    def get_sql_database(self) -> Any:
        """Retorna um SQLDatabase pronto para uso com LangChain e LangGraph."""
        if self._engine is None:
            raise RuntimeError("PostgreSQL não está conectado")

        try:
            from langchain_community.utilities import SQLDatabase
        except ImportError as exc:
            raise RuntimeError(
                "langchain-community is required to use get_sql_database()"
            ) from exc

        return SQLDatabase(self._engine)
