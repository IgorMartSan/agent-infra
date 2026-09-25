# Workers

O Compose padrão executa [`py-agent-job`](py-agent-job/README.md) três vezes, com uma fila e um `AGENT_ID` para cada agente. Esse worker recebe a mensagem do gateway, executa o grafo selecionado e publica um evento Redis. O catálogo de agentes fica em `src/agents/__init__.py`; cada agente mantém seus arquivos em `src/agents/langchain_agents/<nome>/`.

Os jobs abaixo são implementações independentes e permanecem em suas próprias pastas:

| Serviço | Papel | Compose padrão |
| --- | --- | --- |
| [`py-simple-agent-job`](py-simple-agent-job/README.md) | Exemplo que repete mensagens | Perfil `legacy` como `worker-agent` |
| [`py-sql-agent-job`](py-sql-agent-job/README.md) | Agente SQL original, base do Argus | Não |
| [`py-rsa-agent-job`](py-rsa-agent-job/README.md) | Variante RSA anterior ao worker unificado | Não |
| [`py-gemma4-agent-job`](py-gemma4-agent-job/README.md) | Variante de chat com modelo local | Não |
| [`py-message-delivery`](py-message-delivery/README.md) | Exemplo com fila RabbitMQ de saída | Não |

Cada agente ativo tem um heartbeat `agent:online:{agent_id}` no Redis. O gateway só aceita mensagens para agentes com heartbeat e limita a fila antes de publicar. Não execute dois workers com a mesma fila em paralelo, pois eles dividem as mensagens.
