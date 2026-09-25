// Configuração compartilhada pelos endpoints executados no servidor Next.js.
export const apiBaseUrl = (
  process.env.CHAT_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "")

export const redisUrl =
  process.env.CHAT_REDIS_URL ??
  (process.env.NODE_ENV === "production"
    ? "redis://redis:6379/0"
    : "redis://localhost:6379/0")
