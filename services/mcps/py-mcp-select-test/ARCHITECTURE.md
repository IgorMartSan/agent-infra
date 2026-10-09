# Arquitetura: py-mcp-select-test

## 1. Responsabilidade do Módulo

O `py-mcp-select-test` é um servidor FastMCP de referência e testes para consultas SQL diretas usando `asyncpg`. Ele demonstra a estrutura mínima recomendada para ferramentas que expõem inspeção de tabelas e esquemas para modelos de linguagem via stdio.

---

## 2. Estrutura de Pastas

```text
services/mcps/py-mcp-select-test/
├── src/
│   ├── main.py               # Entrypoint (mcp.run sobre stdio)
│   ├── server.py             # Instanciação do servidor FastMCP
│   └── tools/                # Implementação das ferramentas @mcp.tool()
│       ├── db_tool.py        # Ferramenta list_tables com asyncpg direto
│       └── __init__.py
├── pyproject.toml
└── README.md
```

---

## 3. Diretrizes de Uso

- Usado para validações isoladas e suites de teste manuais ou de desenvolvimento.
- Toda nova ferramenta deve ser decorada com `@mcp.tool()` e registrada explicitamente em `tools/`.
