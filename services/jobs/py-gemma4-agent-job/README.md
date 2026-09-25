# Gemma 4 Agent Job

Variante independente que envia a mensagem ao modelo compatível com a API OpenAI e publica a resposta no Redis Pub/Sub. `src/graph/` monta o grafo, `src/model.py` configura `ChatOpenAI`, `src/processor.py` valida a mensagem e `src/main.py` consome a fila RabbitMQ. Este job não faz parte do Compose padrão.

Configure `.env` a partir de `.env.example`. `AGENT_ID=gemma4-agent` corresponde à chave `agent.gemma4` e à fila `agent.gemma4.requests`. Defina `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY` e os parâmetros de limite e tempo conforme o servidor disponível. O gateway aceita texto no campo `message`.

~~~powershell
cd services/jobs/py-gemma4-agent-job
uv sync --frozen
uv run pytest tests
~~~

Para ativar esse job, adicione seu serviço ao Compose usando o Dockerfile da pasta e as variáveis do broker/Redis do mesmo ambiente. A resposta segue `chat:response:{application_id}:{chat_id}`.
