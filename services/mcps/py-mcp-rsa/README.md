# MCP RSA

Servidor FastMCP usado pelo `rsa-agent` para consulta de serviços ativos, formulários e demandas com sanitização de dados sensíveis.

## Arquitetura do Servidor MCP

A arquitetura detalhada de pastas, contratos e diretrizes de segurança deste servidor estão documentadas em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)


## Banco

O MCP lê suas próprias variáveis `DB_*` em `services/mcps/py-mcp-rsa/.env`; o agente RSA não monta nem repassa essas variáveis. O Dockerfile copia esse arquivo para o container e ajusta `DB_HOST=host.docker.internal`, pois `127.0.0.1` dentro do container aponta para ele próprio. Configure `DB_PORT`, `DB_PASSWORD` e os nomes `DB_NAME`/`DB_USER`, ou seus aliases `DB_DATABASE`/`DB_USERNAME`. `DB_SCHEMA` seleciona as tabelas listadas pela ferramenta; esse schema precisa existir no banco. Reconstrua a imagem após alterar o `.env` do MCP.

A ferramenta consulta `information_schema` e devolve nomes, tipos e quantidade de colunas das tabelas base. Se o schema não existir, a conexão ainda pode funcionar, mas `list_tables` responderá que não há tabelas. O MCP não participa de consultas SQL do `argus-agent`.

## Tools

- `list_tables`: lista tabelas e colunas do schema configurado.
- `list_services_with_done_examples`: fornece ao agente os serviços ativos, seus formulários, o caminho no menu e até três demandas `DONE` por serviço. Use para listar o catálogo ou recomendar serviços a partir de uma necessidade, como "quero instalar câmeras". As demandas são escolhidas por `demand.created_at DESC, demand.id DESC`. A tool apenas consulta os dados; o agente decide o que apresentar ao usuário.

`list_services_with_done_examples` usa três consultas de leitura em lote: serviços com o menu Catálogo e a hierarquia de categorias, campos ativos do formulário e exemplos. O caminho vem de `navigation_menuitem` e dos ancestrais de `catalog_category`. Cada pergunta do formulário continua separada, mesmo quando reutiliza a mesma definição de campo. `ticket.form_data` é histórico e nunca substitui a definição atual do formulário. A saída não contém IDs e tem este esquema:

~~~json
{
  "services": [
    {
      "name": "Nome do serviço",
      "category": "Categoria ou null",
      "menu_path": ["Catálogo", "Categoria", "Nome do serviço"],
      "short_description": "Resumo",
      "description": "Descrição em texto limpo",
      "form": [
        {
          "group": "Nome do grupo ou null",
          "label": "Rótulo exibido",
          "type": "TEXTAREA",
          "required": true,
          "help_text": "Ajuda",
          "options": []
        }
      ],
      "examples": [
        {
          "request_name": "Nome da requisição",
          "demand_name": "Nome da demanda",
          "demand_description": "Descrição técnica",
          "request_answers_summary": "Respostas textuais históricas úteis"
        }
      ]
    }
  ]
}
~~~

Serviços sem demandas concluídas retornam `examples: []`. Quando a entrada Catálogo não está configurada no menu, `menu_path` é uma lista vazia. Respostas de contato, centro de custo, credenciais, anexos e outros campos pessoais são omitidas do resumo; padrões de e-mail, telefone, documento, URL, segredo e códigos históricos são removidos dos textos. Nomes, descrições e respostas são limitados em tamanho. A filtragem de texto livre é baseada em padrões e deve ser revisada antes de usar estes dados fora do ambiente de teste.

~~~powershell
cd services/mcps/py-mcp-rsa
uv sync --frozen
uv run python src/main.py
uv run python -m unittest discover -s tests -v
~~~

Execução direta usa stdio, portanto a saída só aparece quando um cliente MCP chama a ferramenta. Para testar o banco local sem o agente, abra uma sessão via `src/infra/postgresql/connection.py` ou use os logs do `agent-rsa` após uma pergunta sobre tabelas.
