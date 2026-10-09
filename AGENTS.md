# [AGENTS.md](http://AGENTS.md)

Este arquivo define qual fluxo deve ser utilizado para cada solicitação.

Existem somente dois tipos de tarefa:

```
DEVELOPMENT
REVIEW
```

Antes de executar qualquer atividade, classifique a solicitação em um desses dois tipos.

---

# DEVELOPMENT

Utilize `DEVELOPMENT` quando o pedido envolver:

- criar funcionalidade;
- modificar funcionalidade;
- corrigir bug;
- refatorar código;
- criar endpoint;
- modificar endpoint;
- criar ou alterar interface;
- alterar banco de dados;
- alterar infraestrutura;
- criar ou modificar testes;
- implementar integração;
- alterar comportamento existente.

Depois de classificar como `DEVELOPMENT`, siga obrigatoriamente:

```
skills/development.md
```

---

# REVIEW

Utilize `REVIEW` somente quando o pedido for explicitamente para revisar alterações pendentes.

Exemplos:

- revisar os reviews;
- validar os reviews;
- revisar `.review/`;
- verificar alterações pendentes;
- revisar implementações realizadas;
- processar arquivos de revisão.

Depois de classificar como `REVIEW`, siga obrigatoriamente:

```
skills/review.md
```

---

# Regra de classificação

Se o usuário estiver pedindo uma alteração no sistema:

```
DEVELOPMENT
```

Se o usuário estiver pedindo para revisar alterações já realizadas:

```
REVIEW
```

Não misture os dois fluxos.

Uma tarefa `DEVELOPMENT` deve criar um registro em `.review/`.

Uma tarefa `REVIEW` deve processar os registros existentes em `.review/`.

---

# Fluxo

```
PEDIDO DO USUÁRIO
       ↓
CLASSIFICAR
       ↓
 ┌───────────────┐
 │               │
 ↓               ↓
DEVELOPMENT     REVIEW
 │               │
 ↓               ↓
skills/         skills/
development.md  review.md
```

Após a classificação, seguir o arquivo correspondente até a conclusão.