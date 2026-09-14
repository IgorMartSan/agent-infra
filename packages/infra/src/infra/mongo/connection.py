import logging
from pymongo import MongoClient
from pymongo.database import Database

logger = logging.getLogger(__name__)


class MongoConnection:
    """
    Gerencia a conexão com o MongoDB.

    Responsável por:
    - Criar conexão única
    - Validar conexão
    - Expor o database

    NÃO deve conter lógica de negócio.
    """

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database_name: str = "app_db",
    ):
        self.uri = uri
        self.database_name = database_name

        self._client: MongoClient | None = None
        self._database: Database | None = None

        self._connect()

    def _connect(self) -> None:
        """Inicializa a conexão com o MongoDB."""
        try:
            self._client = MongoClient(self.uri)

            # valida conexão
            self._client.admin.command("ping")

            self._database = self._client[self.database_name]

            logger.info("Conectado ao MongoDB com sucesso")

        except Exception:
            logger.exception("Erro ao conectar no MongoDB")
            raise

    def get_database(self) -> Database:
        """Retorna o database ativo."""
        if self._database is None:
            raise RuntimeError("MongoDB não está conectado")
        return self._database
