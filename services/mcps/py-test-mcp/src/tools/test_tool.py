from server import mcp


@mcp.tool()
def hello(name: str) -> str:
    """Diz olá para alguém."""
    return f'Hello, {name}!'
