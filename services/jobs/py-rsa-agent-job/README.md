# RSA Agent Job independente

Variante anterior ao `rsa-agent` do [worker unificado](../py-agent-job/README.md). Consome a fila `agent.rsa.requests`, inicia um servidor MCP por stdio para listar tabelas e usa o modelo configurado para responder. Não está habilitado no Compose padrão; não execute os dois workers RSA na mesma fila.

`src/graph/` contém a chamada MCP e o grafo; `src/processor.py` valida a mensagem; `src/main.py` cuida de RabbitMQ, heartbeat Redis e resposta Pub/Sub. Para execução separada, defina `MCP_SERVER_PATH` apontando para `services/mcps/py-mcp-rsa/src/main.py`, o Python do ambiente do MCP, as variáveis do banco e as configurações `RABBITMQ_*`, `REDIS_*` e `OPENAI_*`.

~~~powershell
cd services/jobs/py-rsa-agent-job
uv sync --frozen
uv run python src/main.py
~~~

O serviço mais recente no Compose é `agent-rsa`. Para acompanhar seu funcionamento, use `docker-compose -f docker-compose.yml logs agent-rsa` na raiz.
