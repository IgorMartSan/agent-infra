"""Exemplos de RESOURCES.

Resource = dados que o cliente pode LER, identificados por uma URI.
É o mecanismo de "expor conteúdo": arquivos de config, documentação,
esquemas, registros. Diferente da tool, um resource não executa lógica
nem altera estado — apenas devolve conteúdo para dar CONTEXTO ao modelo.

Casos de uso típicos:
  - expor documentação/FAQ que o modelo pode consultar
  - expor schema de banco ou arquivo de configuração
  - expor logs ou dados de referência

Uso (o que o cliente envia ao servidor):
  resources/read  {"uri": "config://app"}
  -> resultado: conteúdo do resource como texto

Diferença dos outros conceitos:
  - Tool: o modelo CHAMA para executar algo (resource só é lido)
  - Prompt: mensagem pronta; resource é dado bruto
"""

from server import mcp

# Dado fake que "estaria" em banco ou arquivo de config
APP_CONFIG = {
    'app_name': 'Test MCP',
    'version': '0.1.0',
    'database_url': 'postgresql://user:pass@localhost:5432/app',
}


@mcp.resource('config://app')
def get_app_config() -> str:
    """Expõe a configuração da aplicação.

    O cliente lê via resources/read com a URI "config://app"
    e pode usar o conteúdo como contexto para responder perguntas
    sobre a configuração do sistema.
    """
    import json

    return json.dumps(APP_CONFIG, indent=2)


@mcp.resource('data://users/{user_id}')
def get_user_profile(user_id: int) -> str:
    """Expõe o perfil de um usuário, com URI parametrizada.

    Exemplos de uso (o cliente escolhe a URI):
      resources/read  {"uri": "data://users/1"}   -> perfil do usuário 1
      resources/read  {"uri": "data://users/42"}  -> perfil do usuário 42

    Também é listável em resources/templates/list, pois a URI tem
    parâmetros dinâmicos.
    """
    # Aqui haveria uma consulta ao banco; simulamos a resposta
    return f'Usuário {user_id}: Igor (igor@example.com)'