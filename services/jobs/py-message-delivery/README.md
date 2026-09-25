# Message Delivery Job

Exemplo independente de entrega entre filas RabbitMQ. Consome uma mensagem, executa o processador simples e publica o resultado em `RABBITMQ_OUTBOUND_QUEUE`. O Compose padrão não o inicia; o chat atual recebe respostas pelo Redis dos outros workers.

`src/main.py` organiza consumo e reconexão; `src/processor.py` executa o agente; `src/infra/rabbitmq/` implementa conexão, consumo e publicação. `src/exemples/` contém exemplos de agentes.

Configure `RABBITMQ_HOST/PORT/USER/PASSWORD/VHOST`, `RABBITMQ_EXCHANGE`, `RABBITMQ_QUEUE`, `RABBITMQ_ROUTING_KEY` e `RABBITMQ_OUTBOUND_QUEUE`. A fila de entrada padrão é `agent.simple.requests`; não execute este exemplo junto de outro consumidor dessa fila quando quiser respostas previsíveis no chat.

~~~powershell
cd services/jobs/py-message-delivery
uv sync --frozen
uv run pytest tests
~~~
