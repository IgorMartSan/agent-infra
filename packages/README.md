# Pacotes Compartilhados (`packages/`)

Este diretório contém bibliotecas e pacotes Python reutilizáveis distribuídos localmente entre os serviços do monorepo via instalações editáveis (`uv`).

## Pacotes Disponíveis:
- **[`config`](config/README.md):** Utilitários de logging estruturado centralizado (`setup_logger`).
- **[`infra`](infra/README.md):** Adaptadores de persistência e repositórios reutilizáveis para PostgreSQL, Redis e MongoDB.

## Arquitetura Obrigatória:
Consulte [`ARCHITECTURE.md`](../ARCHITECTURE.md#35-padrão-5-pacotes-compartilhados-packagespackage-name) e os arquivos `ARCHITECTURE.md` individuais de cada pacote.
