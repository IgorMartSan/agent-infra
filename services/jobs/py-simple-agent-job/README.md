# Simple Agent Job

Implementação independente de referência. Consome `agent.simple.requests`, executa um grafo LangGraph que repete a mensagem e publica `message.completed` no Redis. `src/processor.py` valida a entrada; `src/main.py` controla RabbitMQ e Redis. O gateway e o chat são serviços separados.

O Compose padrão executa `agent-simple` a partir de `py-agent-job`. Esta variante pode ser iniciada com o perfil `legacy` como `worker-agent`, desde que `agent-simple` esteja parado: ambos usam a mesma fila. Configure `.env` a partir de `.env.example`, com host e porta internos quando executar pelo Docker.

~~~powershell
cd services/jobs/py-simple-agent-job
uv sync --frozen
uv run pytest tests
~~~

`chat.py` é um cliente de console da API e do Redis; configure `CHAT_API_URL` e `REDIS_HOST/PORT` para o ambiente em que o executar.
