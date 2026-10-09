# config

Pacote local com `config.logger.setup_logger`, usado para configurar os logs da API e do worker unificado. O formato inclui data, nível, arquivo e mensagem; o nível vem de `LOG_LEVEL` nos processos que o usam.

## Arquitetura de Pacotes Compartilhados

A especificação deste pacote e diretrizes de dependências estão documentadas em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)


`packages/config/pyproject.toml` define o pacote. A API e o worker o instalam como dependência local via `uv` (`editable = true`); não é um serviço de rede nem é iniciado separadamente.
