# Chat Next.js

Interface de teste do fluxo completo. O usuário escolhe um agente ativo, envia a mensagem ao gateway por `app/api/chat/route.ts` e acompanha os eventos `message.completed` e `message.failed` pelo stream SSE em `app/api/chat/stream/route.ts`. A lista de agentes vem de `app/api/agents/route.ts`. O estado da conversa fica na aba do navegador; o chat não carrega histórico antigo.

## Arquitetura do Frontend

A arquitetura completa do Next.js App Router, componentes, rotas BFF e conexões de streaming SSE estão documentadas em:

- 📄 [ARCHITECTURE.md](ARCHITECTURE.md)


### Princípios do Frontend:
- **Backend-For-Frontend (BFF):** Todas as conexões externas (Gateway API e Redis) são mediadas pelas rotas `/api/*` em ambiente de servidor, mantendo as credenciais e endereços protegidos.
- **Server-Sent Events (SSE):** O cliente abre conexão com `/api/chat/stream`, que faz ponte com o canal Redis Pub/Sub do chat, permitindo exibição em tempo real sem polling contínuo.

`lib/chat-server.ts` reúne as URLs usadas pelos endpoints do servidor: `CHAT_API_URL` (padrão `http://localhost:8000`) e `CHAT_REDIS_URL`. No Compose, o chat usa `http://py-agent-gateway-api:8000` e `redis://redis:6379/0`. Para executar Next.js no host com o Redis do Compose, defina `CHAT_REDIS_URL=redis://localhost:6380/0`.

~~~powershell
cd services/frontend/chatbot-next
npm ci
npm run dev
npm run typecheck
npm run lint
~~~

`npm run dev` abre a interface na porta 3000; o Compose publica a versão de produção em http://localhost:3001. A API precisa estar na porta 8000 e o Redis acessível pela URL configurada. O stream envia apenas eventos futuros do canal da conversa; mantenha a conexão aberta antes de enviar uma mensagem.
