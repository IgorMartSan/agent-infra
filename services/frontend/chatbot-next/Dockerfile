FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY services/frontend/chatbot-next/package.json ./package.json
COPY services/frontend/chatbot-next/package-lock.json ./package-lock.json

RUN npm ci --include=dev

COPY services/frontend/chatbot-next/ ./

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]
