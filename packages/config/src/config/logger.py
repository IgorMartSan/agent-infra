import logging
import sys


def setup_logger(level: str = "DEBUG") -> None:
    """
    Configura o logger padrão da aplicação.

    Esta função inicializa o módulo `logging` para enviar todos os logs ao
    `stdout`, permitindo que Docker, Kubernetes e outras plataformas coletem
    automaticamente as mensagens da aplicação.

    Args:
        level: Nível mínimo de log que será exibido. Valores suportados:
            - "DEBUG"
            - "INFO"
            - "WARNING"
            - "ERROR"
            - "CRITICAL"

    Formato do log:
        %(asctime)s    -> Data e hora do log.
        %(levelname)s  -> Nível do log.
        %(filename)s   -> Arquivo onde o log foi gerado.
        %(lineno)d     -> Linha do código.
        %(funcName)s   -> Nome da função.
        %(message)s    -> Mensagem do log.

    Exemplo:
        >>> setup_logger("DEBUG")
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Aplicação iniciada")

    Exemplo de saída:
        2026-06-30 18:45:12,351 | INFO     | main.py:15 | main | Aplicação iniciada
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=(
            "%(asctime)s | "
            "%(levelname)-8s | "
            "%(filename)s:%(lineno)d | "
           # "%(funcName)s | "
            "%(message)s"
        ),
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )