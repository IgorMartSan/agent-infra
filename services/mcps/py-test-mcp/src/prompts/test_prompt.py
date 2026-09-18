"""Exemplos de PROMPTS.

Prompt = template de mensagem reutilizável que o servidor expõe.
É o mecanismo de "padronizar interações": o usuário escolhe o prompt,
preenche os argumentos e o servidor devolve mensagens prontas
(geralmente com contexto e instruções) para iniciar a conversa.

Casos de uso típicos:
  - padronizar revisão de código ("revise este PR com foco em X")
  - gerar resumos de documentos com formato fixo
  - onboarding de novos usuários em um assistente

Uso (o que o cliente envia ao servidor):
  prompts/get  {"name": "review_code", "arguments": {"code": "def add(a, b): ..."}}
  -> resultado: mensagens prontas (role + content) para o LLM

Diferença dos outros conceitos:
  - Tool: o modelo CHAMA durante a conversa (prompt é escolhido antes)
  - Resource: dado bruto; prompt é mensagem formatada com instruções
"""

from server import mcp


@mcp.prompt()
def review_code(code: str) -> str:
    """Prompt de revisão de código.

    Exemplos de uso (o cliente escolhe o prompt e os argumentos):
      prompts/get  {"name": "review_code", "arguments": {"code": "def soma(a,b): return a+b"}}
      -> o modelo recebe a mensagem e responde como revisor

    Também aparece em prompts/list, com a descrição dos argumentos.
    """
    return [
        UserMessage(f'Revise o código abaixo e aponte problemas de legibilidade, bugs e estilo:\n\n{code}'),
    ]


@mcp.prompt()
def summarize_document(document: str, focus: str = 'pontos principais') -> str:
    """Prompt de resumo de documento com foco configurável.

    Exemplos de uso:
      prompts/get  {"name": "summarize_document",
                    "arguments": {"document": "<texto>", "focus": "riscos legais"}}
    """
    return [
        UserMessage(f'Summarize o documento a seguir com foco em {focus}:\n\n{document}'),
    ]