# Servidores MCP (`services/mcps/`)

Servidores Model Context Protocol (FastMCP) que expõem ferramentas de dados, recursos e templates de prompts aos agentes de forma padronizada via transporte `stdio`.

## Servidores Existentes:
- **[`py-mcp-rsa`](py-mcp-rsa/README.md):** Ferramentas para consulta de catálogo, hierarquia de menus e exemplos históricos de demandas no banco PostgreSQL, com sanitização de PII.
- **[`py-mcp-select-test`](py-mcp-select-test/README.md):** Servidor mínimo de exemplo para consultas SQL diretas via asyncpg.
- **[`py-test-mcp`](py-test-mcp/README.md):** Servidor completo de demonstração cobrindo tools, resources e prompts sem dependências externas.

## Arquitetura Obrigatória:
Consulte [`ARCHITECTURE.md`](../../ARCHITECTURE.md#33-padrão-3-servidores-mcp-servicesmcpsmcp-name) e os arquivos `ARCHITECTURE.md` individuais de cada servidor MCP.
