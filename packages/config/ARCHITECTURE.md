# Arquitetura: packages/config

## 1. Responsabilidade do Módulo

O `packages/config` é um pacote compartilhado local do monorepo, projetado para fornecer utilitários de configuração e logging estruturado (`setup_logger`) consistentes para os serviços e workers Python da plataforma.

---

## 2. Estrutura de Pastas

```text
packages/config/
├── src/
│   └── config/
│       ├── logger.py         # Configuração de logger com timestamp, nível e arquivo
│       └── __init__.py
├── pyproject.toml            # Especificação do pacote Python
└── README.md
```

---

## 3. Diretrizes de Uso

1. **Pacote Puro:** Não deve executar processos, abrir portas de rede ou conter listeners.
2. **Dependência Local:** Instalado nos serviços via uv usando `editable = true`:
   ```toml
   [tool.uv.sources]
   config = { path = "../../../packages/config", editable = true }
   ```
3. **Desacoplamento:** Não deve importar código de outros serviços (`services/*`) nem depender de variáveis de ambiente de bancos específicos.
