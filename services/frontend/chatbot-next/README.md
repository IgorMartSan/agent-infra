# Chat Next.js

Interface de teste do fluxo completo. O usuário escolhe um agente ativo, envia a mensagem ao gateway por `app/api/chat/route.ts` e acompanha os eventos `message.completed` e `message.failed` pelo stream SSE em `app/api/chat/stream/route.ts`. A lista de agentes vem de `app/api/agents/route.ts`. O estado da conversa fica na aba do navegador; o chat não carrega histórico antigo.

`lib/chat-server.ts` reúne as URLs usadas pelos endpoints do servidor: `CHAT_API_URL` (padrão `http://localhost:8000`) e `CHAT_REDIS_URL`. No Compose, o chat usa `http://py-agent-gateway-api:8000` e `redis://redis:6379/0`. Para executar Next.js no host com o Redis do Compose, defina `CHAT_REDIS_URL=redis://localhost:6380/0`.

~~~powershell
cd services/frontend/chatbot-next
npm ci
npm run dev
npm run typecheck
npm run lint
~~~

`npm run dev` abre a interface na porta 3000; o Compose publica a versão de produção em http://localhost:3001. A API precisa estar na porta 8000 e o Redis acessível pela URL configurada. O stream envia apenas eventos futuros do canal da conversa; mantenha a conexão aberta antes de enviar uma mensagem.

Para acessar de outro dispositivo, use `http://<IP-da-maquina-host>:3001` com o Compose, ou `http://<IP-da-maquina-host>:3000` com `npm run dev`. O frontend escuta em `0.0.0.0`, sem depender de um IP fixo. As chamadas do navegador usam `/api` no mesmo host; não é necessário trocar `CHAT_API_URL` pelo IP da máquina.

No Windows, libere a porta do Compose em um PowerShell como administrador:

~~~powershell
New-NetFirewallRule -Name "ChatbotNext-TCP-3001" -DisplayName "Chatbot Next TCP 3001" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3001 -Profile Any -RemoteAddress Any
~~~

Se o Docker/WSL publicar a porta somente no loopback do Windows, configure o encaminhamento abaixo no PowerShell como administrador. Encaminhamentos antigos da porta 3001 presos a um IP específico devem ser removidos antes (`netsh interface portproxy show all` para consultar). Não é necessário esse encaminhamento quando o Docker já escuta no IP da rede.

~~~powershell
netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=3001 connectaddress=127.0.0.1 connectport=3001
~~~

O dispositivo precisa ter uma rota até o IP do host. Para acesso pela internet, também é necessário configurar o roteador ou firewall da infraestrutura.
