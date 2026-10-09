# Arquitetura: packages/infra

## 1. Responsabilidade do Módulo

O `packages/infra` é uma biblioteca compartilhada de adaptadores e repositórios reutilizáveis para bancos de dados e sistemas de cache/mensageria (PostgreSQL, Redis e MongoDB). Ele isola a complexidade de persistência genérica e agrupa ferramentas compartilháveis entre múltiplos serviços da plataforma.

---

## 2. Estrutura de Pastas

```text
packages/infra/
├── src/
│   └── infra/
│       ├── mongo/            # Repositórios e conexões com MongoDB
│       │   ├── connection.py
│       │   ├── longtermrepository.py
│       │   └── shorttermrepository.py
│       ├── postgres/         # Message store e adaptadores PostgreSQL
│       │   ├── connection.py
│       │   └── message_store.py
│       └── redis/            # Repositórios para agrupamento e controle em Redis
│           ├── connection.py
│           ├── message_group_repository.py
│           └── response_repository.py
├── tests/                    # Testes de integração isolados
│   └── redis/
│       └── test_message_group_repository_integration.py
├── pyproject.toml            # Dependências SQLAlchemy, psycopg2, redis, pymongo
└── README.md
```

---

## 3. Diretrizes de Uso e Limites de Escopo

1. **Reutilização Opcional e Explícita:** Serviços com requisitos específicos de ciclo de vida e concorrência (como o Gateway assíncrono e os Workers de agente) podem manter adaptadores dedicados em seus próprios diretórios `src/infra/`. O `packages/infra` fornece blocos de construção consolidados e compartilhados.
2. **Ambientes de Teste Isolados:** Testes de integração contidos neste pacote utilizam bancos e instâncias dedicadas (ex: `TEST_REDIS_DB`), nunca interferindo no DB 0 ou no ambiente de execução padrão.
3. **Sem Efeitos Colaterais:** A importação de módulos deste pacote não deve inicializar conexões de rede automaticamente; conexões devem ser abertas sob demanda ou em métodos de inicialização explícitos.
