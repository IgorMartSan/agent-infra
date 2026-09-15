import json
import logging
import os
from typing import Any

import sqlparse
from langchain.tools import tool
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from infra.sql_database import get_database_engine

logger = logging.getLogger(__name__)


def _schema() -> str:
    return os.getenv("SQL_DATABASE_SCHEMA", "public").strip() or "public"


def _database_error(operation: str, error: Exception) -> str:
    logger.exception("Falha ao %s no banco SQL", operation, exc_info=error)
    return (
        f"Não foi possível {operation}. Verifique a conexão e as permissões "
        "somente de leitura configuradas para o usuário do banco."
    )


def _validate_read_only_query(query: str) -> str:
    statements = [statement for statement in sqlparse.parse(query) if str(statement).strip()]
    if len(statements) != 1:
        raise ValueError("Envie exatamente uma instrução SQL por consulta.")

    statement = statements[0]
    statement_type = statement.get_type().upper()
    normalized = str(statement).strip()
    first_keyword = normalized.split(maxsplit=1)[0].upper() if normalized else ""

    if statement_type != "SELECT" and first_keyword not in {"EXPLAIN", "SHOW"}:
        raise ValueError("Somente SELECT, WITH ... SELECT, EXPLAIN e SHOW são permitidos.")

    return normalized.rstrip(";").strip()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


@tool
def list_database_objects() -> str:
    """Lista tabelas e views disponíveis no schema PostgreSQL configurado."""
    try:
        inspector = inspect(get_database_engine())
        schema = _schema()
        return json.dumps(
            {
                "schema": schema,
                "tables": inspector.get_table_names(schema=schema),
                "views": inspector.get_view_names(schema=schema),
            },
            ensure_ascii=False,
        )
    except (RuntimeError, SQLAlchemyError) as error:
        return _database_error("listar tabelas e views", error)


@tool
def describe_database_tables(table_names: list[str]) -> str:
    """Retorna colunas e chaves das tabelas informadas. Use antes de escrever uma consulta."""
    try:
        inspector = inspect(get_database_engine())
        schema = _schema()
        available = set(inspector.get_table_names(schema=schema)) | set(
            inspector.get_view_names(schema=schema)
        )
        descriptions: dict[str, Any] = {}

        for table_name in table_names:
            if table_name not in available:
                descriptions[table_name] = {"error": "Tabela ou view não encontrada."}
                continue

            descriptions[table_name] = {
                "columns": [
                    {
                        "name": column["name"],
                        "type": str(column["type"]),
                        "nullable": column.get("nullable"),
                    }
                    for column in inspector.get_columns(table_name, schema=schema)
                ],
                "primary_key": inspector.get_pk_constraint(table_name, schema=schema).get(
                    "constrained_columns", []
                ),
                "foreign_keys": inspector.get_foreign_keys(table_name, schema=schema),
            }

        return json.dumps(descriptions, ensure_ascii=False, default=str)
    except (RuntimeError, SQLAlchemyError) as error:
        return _database_error("descrever as tabelas", error)


@tool
def execute_read_only_sql(query: str) -> str:
    """Executa uma consulta SQL somente de leitura e retorna no máximo o limite configurado de linhas."""
    try:
        safe_query = _validate_read_only_query(query)
    except ValueError as error:
        return f"Consulta recusada: {error}"

    max_rows = max(1, int(os.getenv("SQL_MAX_ROWS", "100")))

    try:
        with get_database_engine().connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ ONLY"))
                result = connection.execute(text(safe_query))
                if not result.returns_rows:
                    return "Consulta recusada: a instrução não retornou linhas."

                rows = result.fetchmany(max_rows + 1)
                payload = {
                    "columns": list(result.keys()),
                    "rows": [[_json_value(value) for value in row] for row in rows[:max_rows]],
                    "row_count": min(len(rows), max_rows),
                    "truncated": len(rows) > max_rows,
                }
                return json.dumps(payload, ensure_ascii=False)
            finally:
                transaction.rollback()
    except (RuntimeError, SQLAlchemyError) as error:
        return _database_error("executar a consulta", error)


SQL_TOOLS = [list_database_objects, describe_database_tables, execute_read_only_sql]
