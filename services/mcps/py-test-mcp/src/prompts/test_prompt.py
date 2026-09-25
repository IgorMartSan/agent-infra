"""Templates de mensagem registrados no servidor de demonstração."""

from server import mcp


@mcp.prompt()
def review_code(code: str) -> str:
    """Pede uma revisão de legibilidade, bugs e estilo."""
    return f"Revise o código abaixo e aponte problemas de legibilidade, bugs e estilo:\n\n{code}"


@mcp.prompt()
def summarize_document(document: str, focus: str = "pontos principais") -> str:
    """Pede um resumo com o foco informado pelo cliente."""
    return f"Resuma o documento a seguir com foco em {focus}:\n\n{document}"
