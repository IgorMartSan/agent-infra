import tools  # noqa: F401  (carrega e registra as tools no mcp)

from server import mcp

if __name__ == '__main__':
    mcp.run()
