# Avaliação de respostas por agente

Cada agente tem uma planilha em `cases/`: `simple-agent.xlsx`, `rsa-agent.xlsx` ou `argus-agent.xlsx`.

## Preencher perguntas

Na aba **Casos**, preencha uma linha por pergunta. Não altere os nomes das colunas:

| Coluna | Uso |
| --- | --- |
| `id` | Identificador único do caso. |
| `question` | Pergunta enviada ao agente. |
| `reference` | Resposta esperada ou fatos essenciais. |
| `mode` | `exact`, `contains` ou `semantic`. |

`exact` exige texto igual (ignorando espaços nas pontas). `contains` procura o trecho esperado, sem diferenciar maiúsculas. `semantic` usa a LLM como juiz para comparar o sentido. Em todos os modos, a LLM atribui notas de 0 a 5 para correção factual, completude, relevância, aderência às instruções e clareza. Nos modos `exact` e `contains`, a aprovação continua determinada pela comparação objetiva, mesmo quando a LLM atribui uma nota alta.

A avaliação considera apenas a pergunta, a resposta de referência e a resposta do agente. Não verifica fatos em fontes externas. O mesmo modelo configurado para o agente atua como juiz, sem ferramentas nem memória. Para `simple-agent`, o juiz usa `.env.rsa`.

## Executar

Inicie o Compose. Na pasta `services/jobs/py-agent-job`, rode:

```powershell
uv sync --frozen
uv run pytest evals/test_simple_agent.py -v
uv run pytest evals/test_rsa_agent.py -v
uv run pytest evals/test_argus_agent.py -v
```

Para executar todos, use `uv run pytest evals -v`. O endereço padrão do chat é `http://127.0.0.1:3001`; defina `AGENT_EVAL_BASE_URL` se ele estiver em outro endereço. Cada caso usa uma conversa nova. Os casos RSA e Argus dependem dos bancos configurados para esses agentes.

Ao iniciar os casos de cada agente, a execução recria as abas **Métricas** e **Resumo** da planilha correspondente. A aba **Casos** é preservada. A aba Métricas mostra resposta obtida, aprovação, cinco notas, média, tempo, motivo, sugestão de correção e erros. A aba Resumo calcula totais, taxa de aprovação e médias. Feche a planilha no Excel antes de executar, pois o Excel pode impedir sua gravação.

Se já existir um arquivo `.csv` com o mesmo nome da planilha, ele também é reescrito a cada execução com os casos e os resultados atuais. O CSV é uma exportação; edite as perguntas na aba **Casos** do `.xlsx`.

Os arquivos JSON em `cases/` são cópias anteriores à migração e não são lidos pelo avaliador. A suíte `pytest tests` continua separada destas avaliações. A LLM sugere melhorias na planilha, mas não altera o código nem o prompt do agente automaticamente.
