# Arquitetura: py-test-mcp

## 1. Responsabilidade do Módulo

O `py-test-mcp` é um servidor FastMCP de testes completos sem dependências de bancos externos. Ele serve como referência padrão para servidores MCP que implementam a tríade completa de recursos do protocolo: **ferramentas (tools)**, **recursos de contexto (resources)** e **prompts de sistema (prompts)**.

---

## 2. Estrutura de Pastas

```text
services/mcps/py-test-mcp/
├── src/
│   ├── main.py               # Ponto de entrada stdio que carrega promts, resources e tools
│   ├── server.py             # Instância do FastMCP("py-test-mcp")
│   ├── prompts/              # Templates de prompts (@mcp.prompt())
│   │   ├── test_prompt.py
│   │   └── __init__.py
│   ├── resources/            # Recursos de leitura (@mcp.resource())
│   │   ├── test_resource.py
│   │   └── __init__.py
│   └── tools/                # Ferramentas executáveis (@mcp.tool())
│       ├── test_tool.py
│       └── __init__.py
├── Dockerfile                # Build isolado da imagem de teste
├── pyproject.toml
└── README.md
```

---

## 3. Diretrizes de Uso

- Serve como ambiente de teste rápido para validar adaptadores MCP de novos agentes sem a necessidade de infraestrutura de banco de dados ou credenciais ativas.
