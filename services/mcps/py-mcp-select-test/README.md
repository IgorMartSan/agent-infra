# MCP SELECT de exemplo

Servidor FastMCP independente que registra a ferramenta `list_tables` em `src/tools/db_tool.py`. Diferentemente do MCP RSA ativo, esta variante usa `asyncpg` diretamente e não é iniciada pelo Compose padrão.

## Arquitetura do Serviço

A arquitetura e estrutura de pastas deste servidor estão documentadas em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)


Defina `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e `DB_SCHEMA` no ambiente do processo; os defaults do código são apenas valores de demonstração. `src/main.py` registra as ferramentas e inicia o transporte stdio.

~~~powershell
cd services/mcps/py-mcp-select-test
uv sync --frozen
uv run python src/main.py
~~~
