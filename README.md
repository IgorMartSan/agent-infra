# Plataforma de agentes

A aplicação recebe mensagens no gateway FastAPI, envia cada uma para a fila RabbitMQ do agente escolhido e publica a resposta no Redis Pub/Sub. O chat Next.js acompanha a conversa por SSE. O Compose principal mantém Redis, RabbitMQ, PostgreSQL local, API, chat e três agentes.

## Iniciar

Na raiz do repositório:

~~~powershell
docker-compose -f docker-compose.yml up -d --build
docker-compose -f docker-compose.yml ps
~~~

O chat abre em http://localhost:3001; a API responde em http://localhost:8000 e documenta os endpoints em http://localhost:8000/docs. O painel RabbitMQ usa a porta 15673 e o Redis Insight a 50030. Os arquivos `.env` usados pelo Compose precisam estar presentes; os arquivos `.env.example` dos serviços mostram as chaves necessárias. Defina credenciais próprias antes de compartilhar o projeto.

## Fluxo atual

```mermaid
flowchart LR
    U[Usuário] --> C[Chat Next.js]
    C -->|POST /api/v1/messages| G[Gateway FastAPI]

    G --> V{Valida agente, conversa
    e capacidade da fila}
    V -->|Falha: 503 ou 409| E[Resposta de erro]
    E --> C
    V -->|Válido| Q{Seleciona fila do agente}

    Q -->|agent.simple| RSQ[(RabbitMQ)]
    Q -->|agent.rsa| RRQ[(RabbitMQ)]
    Q -->|agent.argus| RAQ[(RabbitMQ)]
    RSQ --> WS[Worker simple]
    RRQ --> WR[Worker RSA]
    RAQ --> WA[Worker Argus]

    G -->|Confirma publicação: 202 ACCEPTED| C
    WR -. consulta .-> MCP[MCP RSA / PostgreSQL]
    WA -. consulta somente leitura .-> DB[(PostgreSQL)]

    WS -->|message.completed ou message.failed| P[(Redis Pub/Sub)]
    WR -->|message.completed ou message.failed| P
    WA -->|message.completed ou message.failed| P
    P -->|chat:response:{application_id}:{chat_id}| G
    G -->|SSE| C

    WS -. libera conversa e confirma .-> RSQ
    WR -. libera conversa e confirma .-> RRQ
    WA -. libera conversa e confirma .-> RAQ
```

O gateway retorna `202 ACCEPTED` depois da confirmação do broker. Ele recusa agentes sem heartbeat (`503`), conversas ocupadas (`409`) e filas acima do limite (`503`). Cada worker envia `message.completed` ou `message.failed` ao canal Redis, libera o bloqueio da conversa e confirma a mensagem. O Redis Pub/Sub não armazena respostas para clientes que estavam desconectados.

| Agente no chat | Função | Configuração |
| --- | --- | --- |
| `simple-agent` | Repete a mensagem para testar o fluxo | `services/jobs/py-agent-job/.env.simple` |
| `rsa-agent` | Consulta o MCP RSA e o modelo configurado | `services/jobs/py-agent-job/.env.rsa` e `services/mcps/py-mcp-rsa/.env` |
| `argus-agent` | Consulta PostgreSQL em modo somente leitura | `services/jobs/py-agent-job/.env.argus` |

O `agent-rsa` usa `host.docker.internal` para alcançar o PostgreSQL instalado no host. Dentro de um container, `127.0.0.1` aponta para o próprio container. O schema `DB_SCHEMA` precisa existir no banco; um schema ausente produz uma lista vazia de tabelas.

O `rsa-agent` mantém mensagens recentes e um resumo da parte antiga da conversa no estado do LangGraph. Quando o histórico passa de 20 mensagens (`RSA_MEMORY_MAX_MESSAGES`), o nó `summarize` atualiza o resumo e preserva a última troca. Um checkpointer PostgreSQL mantém apenas o estado mais recente de cada conversa, inclusive após o reinício do worker. Esse armazenamento usa o serviço `postgres-vector`, separado do banco RSA consultado pelo MCP.

## Arquitetura Geral do Sistema

A especificação completa das diretrizes arquiteturais, padrões de pastas para cada tipo de serviço e regras de validação para desenvolvimento estão documentadas em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)

Consulte o documento acima antes de criar ou modificar qualquer serviço, agente, API ou pacote.

## Serviços e pacotes

- [Documento de Arquitetura Geral](ARCHITECTURE.md)
- [Gateway](services/apis/py-agent-gateway-api/README.md)
- [Chat](services/frontend/chatbot-next/README.md)
- [Worker dos agentes](services/jobs/py-agent-job/README.md)
- [MCP RSA](services/mcps/py-mcp-rsa/README.md), [MCP SELECT de exemplo](services/mcps/py-mcp-select-test/README.md) e [MCP de teste](services/mcps/py-test-mcp/README.md)
- [Configuração compartilhada](packages/config/README.md) e [infraestrutura reutilizável](packages/infra/README.md)
- [Arquivos Compose](composes/README.md)

`py-agent-job` é o worker usado pelos três agentes do Compose. Cada agente roda em um processo próprio da mesma imagem.

## Skills de apoio ao desenvolvimento

Skills são guias carregados pelo agente de programação durante tarefas de desenvolvimento; elas não são dependências executadas pela aplicação. Para este projeto, mantenha as skills em `.agents/skills/<nome-da-skill>/SKILL.md` e consulte-as ao alterar as partes correspondentes:

| Skill | Quando consultar |
| --- | --- |
| `ecosystem-primer` | Escolher entre LangChain, LangGraph e Deep Agents e identificar o guia específico adequado. |
| `langchain-fundamentals` | Criar ou alterar agentes LangChain, ferramentas e middleware. |
| `langgraph-fundamentals` | Alterar grafos, estado, nós e fluxo de execução LangGraph. |
| `langgraph-persistence` | Alterar persistência de estado, checkpointer, `thread_id` ou memória entre conversas. |
| `langchain-dependencies` | Configurar ou atualizar versões e dependências LangChain/LangGraph. |

As skills acima fazem parte do repositório [langchain-skills](https://github.com/langchain-ai/langchain-skills). Instale-as no projeto com `npx skills add langchain-ai/langchain-skills --skill '*' --yes` ou copie para `.agents/skills/` somente as skills necessárias. Consulte o `SKILL.md` de cada uma para instruções completas.

## Testar uma mensagem

~~~powershell
$body = @{
  application_id = "teste"
  user_id = "usuario-1"
  chat_id = "conversa-1"
  agent_id = "simple-agent"
  message = "Olá"
  delivery = @{ type = "NONE" }
} | ConvertTo-Json -Depth 4
Invoke-RestMethod http://localhost:8000/api/v1/messages -Method Post -ContentType "application/json" -Body $body
~~~

A resposta de `POST` contém o `message_id`; o conteúdo do agente chega pelo stream SSE do chat, após a publicação no Redis. O corpo aceita somente texto no campo `message`.

## Verificação local

~~~powershell
cd services/apis/py-agent-gateway-api
uv run pytest tests
cd ../../jobs/py-agent-job
uv run pytest tests
cd ../../frontend/chatbot-next
npm run typecheck
npm run lint
~~~

Use os READMEs dos serviços para executar suites adicionais. O `architecture.drawio` e componentes em `packages/infra` incluem ideias ou adaptadores que não participam do fluxo padrão acima.
