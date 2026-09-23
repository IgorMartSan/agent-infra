# Configuração específica do Agente SQL
AGENT_ID=sql-agent
RABBITMQ_QUEUE=agent.sql.requests
RABBITMQ_ROUTING_KEY=agent.sql
MCP_SERVER_PATH=/code/services/mcps/py-mcp-select-test/src/main.py
MCP_SERVER_NAME=sql-db
AGENT_SYSTEM_PROMPT=Você é um agente especialista em consultas PostgreSQL. Use as ferramentas MCP para consultar o banco de dados. Execute apenas consultas de leitura. Responda sempre em português do Brasil, de forma clara e objetiva.