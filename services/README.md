# Diretório de Serviços (`services/`)

Este diretório contém todas as aplicações executáveis do ecossistema, agrupadas funcionalmente por responsabilidade arquitetural:

- **[`apis/`](apis/README.md):** APIs RESTful HTTP e gateways de entrada (ex: FastAPI).
- **[`frontend/`](frontend/README.md):** Aplicações de interface com o usuário (ex: Next.js).
- **[`jobs/`](jobs/README.md):** Workers de background, consumidores assíncronos e executores de agentes de IA (LangGraph).
- **[`mcps/`](mcps/README.md):** Servidores Model Context Protocol (FastMCP) que expõem ferramentas de dados seguras.

Para entender a macroarquitetura e os padrões de pastas obrigatórios, consulte o documento principal:
- 📄 [ARCHITECTURE.md](../ARCHITECTURE.md)
