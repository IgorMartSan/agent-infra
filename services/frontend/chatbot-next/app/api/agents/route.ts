import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"

const apiBaseUrl = (
  process.env.CHAT_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "")

export async function GET() {
  try {
    const response = await fetch(`${apiBaseUrl}/api/v1/agents`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    })

    if (!response.ok) {
      return NextResponse.json(
        { detail: `A API retornou o erro ${response.status}.` },
        { status: response.status }
      )
    }

    return NextResponse.json(await response.json())
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar os agentes." },
      { status: 503 }
    )
  }
}
