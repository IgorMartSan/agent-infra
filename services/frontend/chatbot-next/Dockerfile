FROM node:20-alpine

WORKDIR /app

ENV NEXT_TELEMETRY_DISABLED=1

COPY services/frontend/chatbot-next/package.json ./package.json
COPY services/frontend/chatbot-next/package-lock.json ./package-lock.json

RUN npm ci

COPY services/frontend/chatbot-next/ ./

RUN npm run build

ENV NODE_ENV=production

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
