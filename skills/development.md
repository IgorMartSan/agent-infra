# Development

Utilize este fluxo para qualquer tarefa de implementação, alteração, correção ou refatoração.

Fluxo obrigatório:

```
TAREFA
   ↓
ENTENDER
   ↓
LER ARCHITECTURE.md (GLOBAL E MÓDULO)
   ↓
INSPECIONAR O QUE JÁ EXISTE
   ↓
PLANEJAR
   ↓
IMPLEMENTAR
   ↓
PROCURAR REDUNDÂNCIA
   ↓
SIMPLIFICAR
   ↓
TESTAR
   ↓
VALIDAR
   ↓
CRIAR SEU PRÓPRIO .review/
   ↓
FINALIZAR
```

# 1. Entender

Identificar:

- objetivo;
- comportamento esperado;
- módulos afetados;
- restrições;
- integrações;
- resultado esperado.

# 2. Ler arquitetura (ARCHITECTURE.md)

Antes de modificar qualquer código ou criar arquivos:

- ler o [`ARCHITECTURE.md`](http://ARCHITECTURE.md) na raiz do monorepo para entender a macroarquitetura, contratos de comunicação e padrões globais;
- ler o `ARCHITECTURE.md` específico de cada módulo afetado para verificar a **arquitetura de pastas**, camadas e responsabilidades locais;
- ler os [`README.md`](http://README.md) dos módulos afetados apenas para obter uma breve explicação funcional do módulo e instruções de execução;
- entender os padrões existentes e onde a alteração pertence no desenho de pastas;
- verificar se novos arquivos ou funções estão sendo alocados estritamente dentro da estrutura definida no `ARCHITECTURE.md`.

Regra de separação de arquivos e responsabilidades:
- O **`ARCHITECTURE.md` global na raiz** define exclusivamente a macroarquitetura do monorepo, topologia, fluxos globais de comunicação e contratos entre serviços. Não contém árvores de pastas internas dos módulos.
- O **`ARCHITECTURE.md` interno de cada módulo** é onde reside obrigatoriamente a **arquitetura de pastas**, organização de camadas e regras estruturais daquele serviço específico.
- O arquivo **`README.md`** deve conter apenas uma breve explicação do propósito do módulo, variáveis de ambiente e comandos de execução.

Se a estrutura de pastas interna mudar, atualizar obrigatoriamente o `ARCHITECTURE.md` do módulo afetado. Se a macroarquitetura do sistema mudar, atualizar o `ARCHITECTURE.md` global da raiz.

# 3. Inspecionar o projeto

Antes de criar código novo, pesquisar por:

- funções existentes;
- services;
- repositories;
- models;
- schemas;
- helpers;
- componentes;
- endpoints;
- validações;
- regras de negócio;
- testes.

Pergunta obrigatória:

```
Já existe algo que faz isso ou parte disso?
```

Priorizar reutilização.

# 4. Planejar

Criar um plano curto considerando:

- arquivos que serão alterados;
- código que será reutilizado;
- novas funções necessárias;
- impactos;
- testes necessários.

# 5. Implementar

Durante a implementação:

- modificar somente o necessário;
- seguir a arquitetura existente;
- reutilizar código;
- preservar contratos;
- evitar duplicação;
- evitar abstrações desnecessárias;
- criar ou atualizar testes.

# 6. Procurar redundância

Após implementar, procurar:

- funções equivalentes;
- services duplicados;
- helpers duplicados;
- repositories equivalentes;
- schemas repetidos;
- models duplicados;
- validações repetidas;
- regras de negócio duplicadas;
- segunda fonte de verdade;
- abstrações desnecessárias.

Se encontrar:

```
SIMPLIFICAR
   ↓
REUTILIZAR
   ↓
REMOVER DUPLICAÇÃO
```

# 7. Segurança

Verificar quando aplicável:

- autenticação;
- autorização;
- permissões;
- ownership;
- validação de entrada;
- exposição de dados;
- acesso indevido;
- tratamento de erros;
- secrets;
- concorrência;
- condições de corrida.

# 8. Testar

Executar os testes relacionados à alteração.

```
TESTES DA ALTERAÇÃO
   ↓
TESTES DO MÓDULO
   ↓
TESTES DE INTEGRAÇÃO
   ↓
TESTES MAIS AMPLOS
quando necessário
```

Nunca informar que um teste passou sem executá-lo.

# 9. Validar

Antes de finalizar:

```
[ ] solicitação atendida
[ ] arquitetura de pastas e camadas validada contra ARCHITECTURE.md (global e módulo)
[ ] código existente pesquisado
[ ] redundância verificada
[ ] código simplificado
[ ] segurança verificada
[ ] testes executados
[ ] integração validada quando necessária
```

# 10. Criar registro de revisão

Toda tarefa que modificar código deve criar um novo arquivo em:

```
.review/
```

Cada agente deve criar apenas o arquivo referente à sua própria tarefa.

Exemplo:

```
.review/
├── agent-a-create-login.md
├── agent-b-appointment-cancel.md
└── agent-c-provider-availability.md
```

O nome deve ser único e identificar claramente a tarefa.

Preferir formato como:

```
.review/<identificador>-<nome-da-tarefa>.md
```

Exemplos:

```
.review/codex-create-login.md
.review/claude-create-appointment.md
.review/antigravity-provider-calendar.md
```

Se houver possibilidade de colisão, adicionar um identificador adicional:

```
.review/codex-create-login-01.md
```

# 11. Regra de isolamento dos reviews

Durante o fluxo de DEVELOPMENT:

O agente pode:

- criar seu próprio arquivo `.review`;
- atualizar seu próprio arquivo durante a execução da mesma tarefa.

O agente NÃO pode:

- excluir arquivos `.review` de outras tarefas;
- alterar arquivos `.review` de outros agentes;
- renomear arquivos `.review` de outros agentes;
- consolidar vários reviews em um único arquivo;
- considerar reviews existentes como concluídos;
- limpar a pasta `.review/`.

Arquivos existentes em `.review/` devem ser tratados como somente leitura durante DEVELOPMENT.

Exemplo:

```
.review/
├── codex-task-a.md
├── claude-task-b.md
└── antigravity-task-c.md
```

Se o agente estiver executando `task-b`, ele pode modificar apenas:

```
claude-task-b.md
```

Os demais devem permanecer intactos.

# 12. Concorrência entre agentes

Considere que vários agentes podem estar trabalhando ao mesmo tempo.

Portanto:

- não assumir que a pasta `.review/` está estática;
- não apagar arquivos desconhecidos;
- não sobrescrever arquivos existentes;
- não reutilizar nome já existente;
- não modificar review cuja tarefa não seja a atual.

Ao criar um novo arquivo, verificar antes se o nome já existe.

Se existir, escolher outro nome.

# 13. Conteúdo do review

O arquivo deve conter apenas:

```
# Revisão

## Descrição

Breve descrição do que foi implementado.

## Arquivos alterados

- app/appointments/service.py
- app/appointments/router.py

## Funções / classes / endpoints

- AppointmentService.create
- AppointmentService.cancel
- POST /appointments

## Testes relacionados

- tests/test_appointments.py
```

# 14. Regra final

```
DEVELOPMENT
   ↓
IMPLEMENTAR
   ↓
REMOVER REDUNDÂNCIA
   ↓
SIMPLIFICAR
   ↓
TESTAR
   ↓
VALIDAR
   ↓
CRIAR APENAS O SEU .review/
```

Durante DEVELOPMENT, nenhum review de outra tarefa deve ser alterado ou removido.