import prompts  # noqa: F401  (registra os prompts no mcp)
import resources  # noqa: F401  (registra os resources no mcp)
import tools  # noqa: F401  (registra as tools no mcp)

from server import mcp

if __name__ == '__main__':
    mcp.run()