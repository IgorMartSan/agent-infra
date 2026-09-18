# py-test-mcp

Servidor FastMCP de teste, feito para ser enxuto: apenas a inicialização do servidor separada dos arquivos de tools.

## Arquitetura

```text
main.py          → importa server.py e tools/, inicia o servidor
   ↓
server.py        → cria e exporta a única instância do FastMCP
   ↓
tools/
└── test_tool.py → define e registra as tools com @mcp.tool
```

```text
py-test-mcp/
├── Dockerfile
├── pyproject.toml
├── uv.lock
└── src/
    ├── main.py
    ├── server.py
    └── tools/
        ├── __init__.py
        └── test_tool.py
```

### Responsabilidades

| Arquivo | Responsabilidade |
|---|---|
| `src/server.py` | Cria a instância `mcp = FastMCP(name='Test MCP')`. Não importa nada do projeto. |
| `src/tools/*.py` | Cada arquivo importa `mcp` de `server.py` e registra suas tools com `@mcp.tool`. |
| `src/tools/__init__.py` | Importa todos os módulos de tools, para que `import tools` registre tudo. |
| `src/main.py` | Ponto de entrada: importa `tools` (efeito de registro) e chama `mcp.run()`. |

### Sem import circular

O fluxo de dependência é uma só direção:

- `main.py` → `server.py` e `tools/`
- `tools/test_tool.py` → `server.py`
- `server.py` → não importa nada do projeto

## Tools

### `hello`

Recebe um nome e retorna uma saudação.

- **Parâmetros:** `name: str` — nome da pessoa a ser cumprimentada.
- **Retorno:** `str`, no formato `Hello, {name}!`.

Exemplo de resultado:

```text
hello(name="Igor") → "Hello, Igor!"
```

## Instalação e execução

Requisitos: [uv](https://docs.astral.sh/uv/) instalado.

```bash
# instalar dependências (cria o .venv e o uv.lock)
uv sync

# executar o servidor (stdio por padrão)
uv run python src/main.py
```

## Como adicionar uma nova tool

1. Crie `src/tools/minha_tool.py`:

```python
from server import mcp


@mcp.tool()
def minha_tool(x: int) -> int:
    """Descrição curta da tool."""
    return x * 2
```

2. Adicione o import em `src/tools/__init__.py`:

```python
from tools import test_tool  # noqa: F401
from tools import minha_tool  # noqa: F401
```

Pronto: `main.py` registra automaticamente tudo que `tools/` importa.

## Docker

```bash
# a partir da raiz do repositório
docker build -f services/mcps/py-test-mcp/Dockerfile -t py-test-mcp .
docker run -it py-test-mcp
```