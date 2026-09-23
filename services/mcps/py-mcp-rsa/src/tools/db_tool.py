"""Tool que lista todas as tabelas e sua estrutura usando a infra de conexão SQLAlchemy.

Usa a session factory definida em infra/postgresql/connection.py (mesmo padrão da API).
A query consulta information_schema.tables + information_schema.columns para montar
a estrutura de cada tabela no schema configurado via DB_SCHEMA.
"""

from sqlalchemy import text

from infra.postgresql.connection import session_factory
from server import mcp

LIST_TABLES_SQL = text("""
    SELECT
        t.table_name,
        STRING_AGG(
            c.column_name || ' (' || c.data_type ||
            CASE WHEN c.character_maximum_length IS NOT NULL
                 THEN '(' || c.character_maximum_length || ')' ELSE '' END || ')',
            ', ' ORDER BY c.ordinal_position
        ) AS columns,
        COUNT(c.column_name) AS column_count
    FROM information_schema.tables t
    JOIN information_schema.columns c
      ON c.table_schema = t.table_schema AND c.table_name = t.table_name
    WHERE t.table_schema = :schema
      AND t.table_type = 'BASE TABLE'
    GROUP BY t.table_name
    ORDER BY t.table_name;
""")


@mcp.tool()
async def list_tables() -> str:
    """Retorna todas as tabelas do banco e sua estrutura (colunas e tipos).

    Usa a conexão SQLAlchemy async definida em infra/postgresql/connection.py.
    O schema é lido da variável de ambiente DB_SCHEMA (default: 'public').
    """
    import os

    schema = os.getenv('DB_SCHEMA', 'public')
    async with session_factory() as session:
        result = await session.execute(LIST_TABLES_SQL, {'schema': schema})
        rows = result.fetchall()

    if not rows:
        return f'Nenhuma tabela encontrada no schema "{schema}".'

    lines = []
    for row in rows:
        lines.append(f"Tabela {row.table_name} ({row.column_count} colunas):\n  {row.columns}")
    return '\n'.join(lines)