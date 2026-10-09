# Review

Utilize este fluxo somente quando houver um pedido explícito para revisar as alterações pendentes em `.review/`.

Não utilize este fluxo automaticamente depois de uma implementação.

Fluxo:

```
PEDIDO DE REVISÃO
   ↓
LER .review/
   ↓
PEGAR UM ARQUIVO
   ↓
REVISAR ALTERAÇÕES
   ↓
PROCURAR BUGS
   ↓
PROCURAR REDUNDÂNCIA
   ↓
SIMPLIFICAR
   ↓
VERIFICAR SEGURANÇA
   ↓
ANALISAR TESTES
   ↓
TESTAR
   ↓
CORRIGIR
   ↓
TESTAR NOVAMENTE
   ↓
VALIDAR
   ↓
REMOVER .review/
   ↓
PRÓXIMO
```

---

# 1. Ler os reviews

Listar:

```
.review/
```

Cada arquivo representa uma alteração pendente de revisão.

Exemplo:

```
.review/
├── login.md
├── appointments.md
└── availability.md
```

Processar os arquivos individualmente.

---

# 2. Ler o registro

Para cada arquivo, identificar:

- descrição;
- arquivos alterados;
- funções alteradas;
- classes alteradas;
- endpoints alterados;
- testes relacionados.

Depois abrir e analisar o código real.

Não confiar somente no conteúdo do arquivo de revisão.

---

# 3. Revisar a implementação

Antes de validar o código, abrir o [`ARCHITECTURE.md`](http://ARCHITECTURE.md) da raiz e o `ARCHITECTURE.md` do módulo afetado.

Verificar:

- **Arquitetura de pastas (Módulo):** os arquivos novos ou alterados foram alocados rigorosamente na estrutura de pastas definida no `ARCHITECTURE.md` do módulo afetado?
- **Macroarquitetura (Global):** a implementação respeita a topologia e contratos globais do `ARCHITECTURE.md` da raiz?
- **Separação de documentação:** o `README.md` contém apenas uma breve explicação/execução do módulo sem duplicar a árvore arquitetural de pastas?
- **Atualização arquitetural:** se a estrutura de pastas mudou, o `ARCHITECTURE.md` do módulo foi atualizado? Se a macroarquitetura mudou, o `ARCHITECTURE.md` da raiz foi atualizado?
- bugs e comportamento incorreto;
- responsabilidades e camadas respeitadas;
- tratamento de erros e exceções;
- regressões e contratos de API/mensageria;
- edge cases.

---

# 4. Procurar redundância

Pesquisar também no restante do projeto.

Verificar:

- funções equivalentes;
- services duplicados;
- helpers repetidos;
- repositories equivalentes;
- schemas repetidos;
- models duplicados;
- validações duplicadas;
- regras de negócio repetidas;
- segunda fonte de verdade.

Perguntas:

```
Isso já existia?

Existe implementação semelhante?

Podemos reutilizar código?

Foram criadas duas formas de fazer a mesma coisa?
```

Se houver redundância, corrigir.

---

# 5. Simplificar

Não limitar a revisão a encontrar bugs.

Também simplificar o código quando possível.

Verificar:

- abstrações desnecessárias;
- funções desnecessariamente grandes;
- código morto;
- imports não utilizados;
- camadas desnecessárias;
- duplicações;
- caminhos diferentes para a mesma regra.

Preferir:

```
MENOS CÓDIGO
+
MENOS DUPLICAÇÃO
+
UMA ÚNICA FONTE DE VERDADE
+
RESPONSABILIDADES CLARAS
```

---

# 6. Segurança

Verificar quando aplicável:

- autenticação;
- autorização;
- permissões;
- ownership;
- validação de entrada;
- exposição de informações;
- acesso entre usuários;
- acesso entre organizações;
- tratamento de secrets;
- queries inseguras;
- condições de corrida;
- concorrência.

---

# 7. Testes

Não confiar apenas nos testes indicados no arquivo `.review`.

O revisor deve:

1. localizar os testes;
2. analisar os testes existentes;
3. executar os testes;
4. procurar cenários não cobertos;
5. criar novos testes quando necessário.

Testar principalmente:

- fluxo normal;
- erro;
- limites;
- validações;
- permissões;
- segurança;
- regressões.

---

# 8. Corrigir

Se encontrar qualquer problema:

```
PROBLEMA
   ↓
CORRIGIR
   ↓
CRIAR / AJUSTAR TESTE
   ↓
EXECUTAR TESTES
   ↓
REVISAR NOVAMENTE
```

As correções fazem parte da própria revisão.

Não criar um novo arquivo `.review` para pequenas correções realizadas durante esse processo.

---

# 9. Validar

Antes de considerar a revisão concluída:

```
[ ] código revisado
[ ] arquitetura de pastas e responsabilidades validada contra ARCHITECTURE.md (global e módulo)
[ ] bugs verificados
[ ] redundância verificada
[ ] código simplificado
[ ] segurança verificada
[ ] testes existentes analisados
[ ] novos testes adicionados quando necessários
[ ] testes executados
[ ] problemas encontrados corrigidos
```

---

# 10. Remover review

Somente depois da validação completa remover:

```
.review/<tarefa>.md
```

Regra:

```
ARQUIVO EXISTE
   ↓
REVISÃO PENDENTE
```

```
ARQUIVO REMOVIDO
   ↓
REVISÃO CONCLUÍDA
```

Nunca remover o arquivo antes da conclusão da revisão.

---

# 11. Próximo arquivo

Depois de concluir um review:

```
REMOVER ARQUIVO
   ↓
PEGAR PRÓXIMO .review
   ↓
REPETIR
```

Continuar até não existirem mais arquivos pendentes ou existir um impedimento que não possa ser resolvido.

---

# Regra final

```
REVIEW
   ↓
REVISAR
   ↓
PROCURAR BUGS
   ↓
REMOVER REDUNDÂNCIA
   ↓
SIMPLIFICAR
   ↓
VERIFICAR SEGURANÇA
   ↓
TESTAR
   ↓
CORRIGIR
   ↓
VALIDAR
   ↓
REMOVER .review/
```

O objetivo do fluxo de revisão é deixar a implementação mais simples, segura, testada e sem redundância antes de considerar o trabalho definitivamente validado.