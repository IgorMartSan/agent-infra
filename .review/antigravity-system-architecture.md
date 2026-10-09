# Revisão

## Descrição

Consolidada a separação estrita da arquitetura: o arquivo ARCHITECTURE.md da raiz contém exclusivamente a macroarquitetura global do monorepo, topologia, contratos de mensageria e diretrizes gerais. Toda e qualquer especificação de arquitetura de pastas interna de cada serviço reside exclusivamente no ARCHITECTURE.md daquele módulo específico. Atualizadas as skills de desenvolvimento (`skills/development.md`) e de revisão (`skills/review.md`) para exigir e validar essa separação.

## Arquivos alterados

- ARCHITECTURE.md
- README.md
- skills/development.md
- skills/review.md
- services/README.md
- services/apis/README.md
- services/apis/py-agent-gateway-api/ARCHITECTURE.md
- services/apis/py-agent-gateway-api/README.md
- services/jobs/README.md
- services/jobs/py-agent-job/ARCHITECTURE.md
- services/jobs/py-agent-job/README.md
- services/jobs/py-agent-job/pyproject.toml
- services/mcps/README.md
- services/mcps/py-mcp-rsa/ARCHITECTURE.md
- services/mcps/py-mcp-rsa/README.md
- services/mcps/py-mcp-select-test/ARCHITECTURE.md
- services/mcps/py-mcp-select-test/README.md
- services/mcps/py-test-mcp/ARCHITECTURE.md
- services/mcps/py-test-mcp/README.md
- services/frontend/README.md
- services/frontend/chatbot-next/ARCHITECTURE.md
- services/frontend/chatbot-next/README.md
- packages/README.md
- packages/config/ARCHITECTURE.md
- packages/config/README.md
- packages/infra/ARCHITECTURE.md
- packages/infra/README.md

## Funções / classes / endpoints

- `ARCHITECTURE.md` (Raiz): Macroarquitetura global exclusiva (topologia, fluxo Mermaid, ciclo de vida de mensagens, fail-fast, presença, lock distribuído e links para os ARCHITECTURE.md internos).
- `ARCHITECTURE.md` (Módulos): Contém a arquitetura de pastas interna detalhada, contratos de camadas e regras de cada serviço.
- `skills/development.md` e `skills/review.md`: Validação clara onde o global valida a macroarquitetura e o ARCHITECTURE.md local valida as pastas do módulo.

## Testes relacionados

- services/apis/py-agent-gateway-api/tests/test_api.py
- services/apis/py-agent-gateway-api/tests/test_agents.py
- services/apis/py-agent-gateway-api/tests/test_message_service.py
- services/apis/py-agent-gateway-api/tests/test_rabbitmq_producer.py
- services/jobs/py-agent-job/tests/test_agent_runtime.py
- services/jobs/py-agent-job/tests/test_argus_agent.py
- services/jobs/py-agent-job/tests/test_rsa_flow_response.py
- services/jobs/py-agent-job/tests/test_simple_agent_chat.py
- services/mcps/py-mcp-rsa/tests/test_catalog_service_tool.py
