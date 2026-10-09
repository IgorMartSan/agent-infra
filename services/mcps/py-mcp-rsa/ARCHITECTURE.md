# Arquitetura: py-mcp-rsa

## 1. Responsabilidade do Módulo

O `py-mcp-rsa` é um servidor Model Context Protocol (FastMCP) que expõe ferramentas seguras para consulta de serviços ativos, hierarquias de menus e demandas concluídas (exemplos históricos) em bancos de dados relacionais PostgreSQL. Ele é executado pelo agente RSA via transporte local `stdio`.

---

## 2. Estrutura de Pastas e Componentes

```text
services/mcps/py-mcp-rsa/
├── src/
│   ├── main.py               # Ponto de entrada que inicializa o servidor FastMCP via stdio
│   ├── server.py             # Instanciação do FastMCP com nome e configurações
│   ├── tools/                # Implementação das ferramentas MCP
│   │   ├── catalog_service_tool.py  # Consultas SQL e sanitização de catálogo/demandas
│   │   └── __init__.py
│   └── infra/                # Clientes de banco e persistência
│       └── postgresql/       # Pool assíncrono de conexões PostgreSQL (asyncpg/SQLAlchemy)
│           ├── connection.py
│           └── __init__.py
├── tests/                    # Testes unitários para sanitização e schemas de dados
│   ├── test_catalog_service_tool.py
│   └── test_connection.py
├── pyproject.toml            # Dependências uv (fastmcp, asyncpg, etc.)
└── README.md                 # Documentação e instruções de configuração
```

---

## 3. Diretrizes de Segurança e Isolamento

1. **Proteção contra Vazamento de Dados (PII):** Todas as respostas de ferramentas devem higienizar dados sensíveis (remover e-mails, telefones, números de documentos, credenciais e dados pessoais) antes de responder ao LLM.
2. **Paginação e Limitação de Janela:** Consultas a bancos devem impor limites restritos (`LIMIT`) para evitar estouro de contexto de tokens no modelo.
3. **Isolamento de Ambiente:** O MCP lê credenciais exclusivamente do seu arquivo `.env` próprio (`services/mcps/py-mcp-rsa/.env`), sem depender das variáveis de ambiente do worker pai.
4. **Modo Somente Leitura:** O usuário de banco configurado deve possuir apenas privilégios de `SELECT` nas tabelas pertinentes.
