# MCP de teste

Servidor FastMCP de demonstração, sem dependência de banco. `src/main.py` registra os módulos e inicia stdio; `src/server.py` cria o servidor. `src/tools/test_tool.py` fornece `hello`, `src/resources/test_resource.py` expõe recursos estáticos de exemplo e `src/prompts/test_prompt.py` fornece templates de revisão e resumo.

~~~powershell
cd services/mcps/py-test-mcp
uv sync --frozen
uv run python src/main.py
~~~

O serviço não entra no Compose padrão. Seu Dockerfile permite construir a imagem na raiz do repositório: `docker build -f services/mcps/py-test-mcp/Dockerfile -t py-test-mcp .`. Recursos e perfis aqui são fictícios e servem apenas para testar clientes MCP.
