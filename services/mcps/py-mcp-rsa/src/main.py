import sys

from fastmcp import FastMCP

mcp = FastMCP(name="DB Infra MCP")

# Disponibiliza a instância mcp para módulos que importam de 'server' ou 'main'
sys.modules["server"] = sys.modules[__name__]
sys.modules["main"] = sys.modules[__name__]

from tools import catalog_service_tool  # registra as ferramentas na instância mcp


if __name__ == "__main__":
    mcp.run()
