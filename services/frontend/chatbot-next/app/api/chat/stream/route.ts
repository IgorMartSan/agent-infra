import { createClient } from "redis"

export const dynamic = "force-dynamic"
export const runtime = "nodejs"

const redisUrl =
  process.env.CHAT_REDIS_URL ??
  (process.env.NODE_ENV === "production"
    ? "redis://redis:6379/0"
    : "redis://localhost:6380/0")

function encodeChannelPart(value: string) {
  return encodeURIComponent(value).replace(
    /[!'()*]/g,
    (character) => `%${character.charCodeAt(0).toString(16).toUpperCase()}`
  )
}

export async function GET(request: Request) {
  const url = new URL(request.url)
  const applicationId = url.searchParams.get("application_id")?.trim()
  const chatId = url.searchParams.get("chat_id")?.trim()

  if (!applicationId || !chatId) {
    return Response.json(
      { detail: "application_id e chat_id são obrigatórios." },
      { status: 400 }
    )
  }

  const channel = `chat:response:${encodeChannelPart(applicationId)}:${encodeChannelPart(chatId)}`
  const subscriber = createClient({ url: redisUrl })
  subscriber.on("error", (error) => {
    console.error("Erro no stream de respostas do Redis:", error)
  })

  try {
    await subscriber.connect()
  } catch {
    return Response.json(
      { detail: "Não foi possível conectar ao canal de respostas." },
      { status: 503 }
    )
  }

  const encoder = new TextEncoder()
  let heartbeat: ReturnType<typeof setInterval> | undefined
  let closed = false

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      async function close() {
        if (closed) return
        closed = true

        if (heartbeat) clearInterval(heartbeat)

        try {
          if (subscriber.isOpen) {
            await subscriber.unsubscribe(channel)
            await subscriber.quit()
          }
        } catch {
          subscriber.destroy()
        }
      }

      request.signal.addEventListener("abort", () => void close(), {
        once: true,
      })

      try {
        await subscriber.subscribe(channel, (message) => {
          if (!closed)
            controller.enqueue(encoder.encode(`data: ${message}\n\n`))
        })

        controller.enqueue(encoder.encode(": connected\n\n"))
        heartbeat = setInterval(() => {
          if (!closed) controller.enqueue(encoder.encode(": keep-alive\n\n"))
        }, 15000)
      } catch {
        await close()
        controller.error(new Error("Falha ao assinar o canal de respostas."))
      }
    },
    async cancel() {
      if (closed) return
      closed = true
      if (heartbeat) clearInterval(heartbeat)

      try {
        if (subscriber.isOpen) {
          await subscriber.unsubscribe(channel)
          await subscriber.quit()
        }
      } catch {
        subscriber.destroy()
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Type": "text/event-stream; charset=utf-8",
      "X-Accel-Buffering": "no",
    },
  })
}
