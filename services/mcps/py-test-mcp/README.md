# py-test-mcp

Servidor FastMCP de teste, feito para ser enxuto: apenas a inicialização do servidor separada dos arquivos de tools, resources e prompts.

## Arquitetura

```text
main.py          → importa server.py e tools/, resources/, prompts/, inicia o servidor
   ↓
server.py        → cria e exporta a única instância do FastMCP
   ↓
tools/       → @mcp.tool       (ações que o LLM chama)
resources/   → @mcp.resource   (dados que o cliente lê, por URI)
prompts/     → @mcp.prompt     (templates de mensagem reutilizáveis)
```

```text
py-test-mcp/
├── Dockerfile
├── README.md
├── pyproject.toml
├── uv.lock
└── src/
    ├── main.py
    ├── server.py
    ├── prompts/
    │   ├── __init__.py
    │   └── test_prompt.py
    ├── resources/
    │   ├── __init__.py
    │   └── test_resource.py
    └── tools/
        ├── __init__.py
        └── test_tool.py
```

### Responsabilidades

| Arquivo | Responsabilidade |
|---|---|
| `src/server.py` | Cria a instância `mcp = FastMCP(name='Test MCP')`. Não importa nada do projeto. |
| `src/tools/*.py` | Cada arquivo importa `mcp` de `server.py` e registra suas tools com `@mcp.tool`. |
| `src/resources/*.py` | Cada arquivo importa `mcp` de `server.py` e registra seus resources com `@mcp.resource`. |
| `src/prompts/*.py` | Cada arquivo importa `mcp` de `server.py` e registra seus prompts com `@mcp.prompt`. |
| `src/tools/__init__.py` (idem resources/prompts) | Importa todos os módulos, para que `import tools` registre tudo. |
| `src/main.py` | Ponto de entrada: importa os pacotes (efeito de registro) e chama `mcp.run()`. |

### Sem import circular

O fluxo de dependência é uma só direção:

- `main.py` → `server.py`, `tools/`, `resources/`, `prompts/`
- `tools/test_tool.py`, `resources/test_resource.py`, `prompts/test_prompt.py` → `server.py`
- `server.py` → não importa nada do projeto

## Tools, Resources e Prompts

| Conceito | Serve para | Decoração | Como o cliente usa |
|---|---|---|---|
| **Tool** | Ação que o LLM *chama* durante a conversa (executar lógica, consultar API, calcular). | `@mcp.tool()` | `tools/call` |
| **Resource** | Dado que o cliente *lê* por URI para dar contexto ao modelo (config, docs, schema). | `@mcp.resource('uri://...')` | `resources/read` |
| **Prompt** | Template de mensagem reutilizável, escolhido antes da conversa começar. | `@mcp.prompt()` | `prompts/get` |

## Tools

### `hello`

```python
@mcp.tool()
def hello(name: str) -> str:
    """Diz olá para alguém."""
    return f'Hello, {name}!'
```

- **Parâmetros:** `name: str`.
- **Retorno:** `str`, no formato `Hello, {name}!`.

Exemplo: `hello(name="Igor")` → `"Hello, Igor!"`

## Resources

### `config://app`

Expõe a configuração da aplicação como JSON.

```python
@mcp.resource('config://app')
def get_app_config() -> str: ...
```

Exemplo: `resources/read {"uri": "config://app"}` → conteúdo do JSON de configuração.

### `data://users/{user_id}`

Resource com URI parametrizada (template). Retorna o perfil de um usuário.

Exemplos: `resources/read {"uri": "data://users/1"}`, `data://users/42`.

## Prompts

### `review_code`

Template de revisão de código: recebe o código e devolve uma mensagem pronta pedindo a revisão.

```python
@mcp.prompt()
def review_code(code: str) -> str: ...
```

Exemplo: `prompts/get {"name": "review_code", "arguments": {"code": "def soma(a,b): return a+b"}}`.

### `summarize_document`

Resumo de documento com foco configurável (`focus` tem default `'pontos principais'`).

Exemplo: `prompts/get {"name": "summarize_document", "arguments": {"document": "<texto>", "focus": "riscos legais"}}`.

## Instalação e execução

Requisitos: [uv](https://docs.astral.sh/uv/) instalado.

```bash
# instalar dependências (cria o .venv e o uv.lock)
uv sync

# executar o servidor (stdio por padrão)
uv run python src/main.py
```

## Como adicionar novos itens

1. Crie `src/tools/minha_tool.py` (tool), `src/resources/minha_resource.py` (resource) ou `src/prompts/meu_prompt.py` (prompt):

```python
from server import mcp


@mcp.tool()
def minha_tool(x: int) -> int:
    """Descrição curta da tool."""
    return x * 2


@mcp.resource('data://status')
def get_status() -> str:
    """Resource com a status da aplicação."""
    return 'ok'


@mcp.prompt()
def meu_prompt(topico: str) -> str:
    """Prompt pronto sobre um tópico."""
    return f'Explique resumidamente: {topico}'
```

2. Adicione o import no `__init__.py` do pacote correspondente:

```python
from tools import test_tool  # noqa: F401
from tools import minha_tool  # noqa: F401
```

Pronto: `main.py` registra automaticamente tudo que os pacotes importam.

## Docker

```bash
# a partir da raiz do repositório
docker build -f services/mcps/py-test-mcp/Dockerfile -t py-test-mcp .
docker run -it py-test-mcp
```