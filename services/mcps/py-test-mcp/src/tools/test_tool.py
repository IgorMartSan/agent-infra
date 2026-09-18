"""Exemplos de TOOLS.

Tool = função que o LLM pode CHAMAR (executar) durante a conversa.
É o mecanismo de "agir": consultar dados, calcular, chamar APIs,
alterar estado. O modelo decide quando chamar e com quais argumentos,
recebe o retorno e continua o raciocínio a partir dele.

Casos de uso típicos:
  - buscar no banco de dados / chamar API externa
  - executar cálculo ou transformação de dados
  - enviar e-mail, gravar arquivo, disparar job

Uso (o que o cliente envia ao servidor):
  tools/call  {"name": "hello", "arguments": {"name": "Igor"}}
  -> resultado: "Hello, Igor!"

Diferença dos outros conceitos:
  - Resource: dados que o cliente LÊ (a tool FAZ algo)
  - Prompt: template de mensagem (a tool executa lógica)
"""


from server import mcp


@mcp.tool()
def hello(name: str) -> str:
    """Diz olá para alguém.

    Args:
        name: nome da pessoa a ser cumprimentada.

    Returns:
        Saudação no formato "Hello, {name}!".
    """
    return f'Hello, {name}!'