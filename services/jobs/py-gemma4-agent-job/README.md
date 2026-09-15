# Gemma 4 Agent Job

Worker baseado no `py-simple-agent-job` que consome mensagens do RabbitMQ, executa o modelo local Gemma 4 por meio de LangChain e publica a resposta no Redis Pub/Sub.

## Modelo

- API compatível com OpenAI: `http://10.247.168.43:8072/v1`
- ID exposto pela API: `gemma4`
- Modelo: `google/gemma-4-E4B-it-qat-w4a16-ct`
- Família: Google Gemma 4 E4B
- Quantização: W4A16
- Contexto total: 4.096 tokens, compartilhado entre entrada e saída
- Saída máxima padrão do cliente: 1.024 tokens
- Servidor: vLLM 0.21.0
- Entradas suportadas pelo servidor: texto, imagem e áudio
- Saída: texto
- Embeddings: não disponíveis

O gateway atual recebe `message` como texto. O modelo suporta conteúdo multimodal, mas o contrato do gateway precisará ser ampliado antes de imagens ou áudio chegarem a este worker.

## Fluxo

1. O gateway recebe uma mensagem para `gemma4-agent`.
2. A chave `agent.gemma4` encaminha a mensagem à fila `agent.gemma4.requests`.
3. O worker executa um `ChatOpenAI` apontando para a API local.
4. A resposta é publicada em `chat:response:{application_id}:{conversation_id}`.
5. O frontend recebe o evento pelo stream SSE.

## Configuração

Copie `.env.example` para `.env` para executar o worker fora do Docker.

Variáveis principais:

| Variável | Padrão | Descrição |
| --- | --- | --- |
| `AGENT_ID` | `gemma4-agent` | Identificador usado pelo gateway |
| `RABBITMQ_QUEUE` | `agent.gemma4.requests` | Fila exclusiva do agente |
| `RABBITMQ_ROUTING_KEY` | `agent.gemma4` | Chave de roteamento |
| `OPENAI_BASE_URL` | `http://10.247.168.43:8072/v1` | URL base compatível com OpenAI |
| `OPENAI_API_KEY` | `EMPTY` | Valor exigido pelo cliente; o servidor não autentica |
| `OPENAI_MODEL` | `gemma4` | Nome publicado por `/v1/models` |
| `OPENAI_MAX_TOKENS` | `1024` | Limite máximo padrão da resposta |
| `OPENAI_TIMEOUT_SECONDS` | `120` | Timeout de inferência |

`RABBITMQ_PREFETCH_COUNT=1` mantém apenas uma mensagem em processamento por instância, de acordo com a capacidade atual do servidor.

## Desenvolvimento

```powershell
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Teste direto do modelo:

```powershell
uv run python src/test_main.py
```
