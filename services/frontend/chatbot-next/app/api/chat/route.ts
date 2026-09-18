import { NextResponse } from "next/server"

const apiBaseUrl = (
  process.env.CHAT_API_URL ??
  "http://localhost:8000"
).replace(/\/$/, "")

export const dynamic = "force-dynamic"

async function readError(response: Response) {
  try {
    const data = (await response.json()) as {
      detail?: string
      message?: string
    }
    return (
      data.detail || data.message || `A API retornou o erro ${response.status}.`
    )
  } catch {
    return `A API retornou o erro ${response.status}.`
  }
}

export async function GET() {
  try {
    const response = await fetch(`${apiBaseUrl}/`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    })

    if (!response.ok) {
      return NextResponse.json(
        { detail: await readError(response) },
        { status: response.status }
      )
    }

    return NextResponse.json({ status: "online" })
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar à API do agente." },
      { status: 503 }
    )
  }
}

export async function POST(request: Request) {
  try {
    const payload: unknown = await request.json()
    const response = await fetch(`${apiBaseUrl}/api/v1/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
    })

    if (!response.ok) {
      return NextResponse.json(
        { detail: await readError(response) },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json(), { status: response.status })
  } catch (error) {
    const detail =
      error instanceof SyntaxError
        ? "O corpo da mensagem é inválido."
        : "Não foi possível conectar à API do agente."
    return NextResponse.json({ detail }, { status: 503 })
  }
}
