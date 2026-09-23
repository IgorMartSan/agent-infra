"""Tool que consulta o banco e retorna todas as tabelas e sua estrutura.

A connection string é lida do .env e montada a partir das variáveis:
  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SCHEMA
"""

import os

from dotenv import load_dotenv

from server import mcp

load_dotenv()

SELECT_SQL = '''
SELECT
    t.table_schema,
    t.table_name,
    STRING_AGG(
        column_name || ' (' || data_type
        || CASE WHEN character_maximum_length IS NOT NULL
            THEN '(' || character_maximum_length || ')' ELSE '' END
        || ')',
        ', '
        ORDER BY ordinal_position
    ) AS columns,
    (SELECT COUNT(*) FROM information_schema.columns c2
     WHERE c2.table_schema = t.table_schema AND c2.table_name = t.table_name) AS column_count
FROM information_schema.tables t
JOIN information_schema.columns c
    ON c.table_schema = t.table_schema AND c.table_name = t.table_name
WHERE t.table_schema = $1
    AND t.table_type = 'BASE TABLE'
GROUP BY t.table_schema, t.table_name
ORDER BY t.table_name;
'''


def _get_connection_kwargs() -> dict:
    """Monta os parâmetros de conexão a partir das variáveis do .env."""
    required = {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'rsa'),
        'user': os.getenv('DB_USER', 'rsa'),
        'password': os.getenv('DB_PASSWORD', 'rsa'),
    }
    return required


def _schema() -> str:
    return os.getenv('DB_SCHEMA', 'public')


async def _run_query() -> list[tuple]:
    import asyncpg

    kwargs = _get_connection_kwargs()
    conn = await asyncpg.connect(**kwargs)
    try:
        return await conn.fetch(SELECT_SQL, _schema())
    finally:
        await conn.close()


@mcp.tool()
async def list_tables() -> str:
    """Retorna todas as tabelas do banco e sua estrutura (colunas e tipos).

    Lê a conexão do .env e consulta o information_schema do PostgreSQL.
    Não recebe parâmetros; o schema é definido pela variável DB_SCHEMA.
    """
    rows = await _run_query()

    if not rows:
        return f'Nenhuma tabela encontrada no schema "{_schema()}".'

    lines = []
    for row in rows:
        lines.append(f"Tabela {row['table_name']} ({row['column_count']} colunas):\n  {row['columns']}")

    return '\n\n'.join(lines)