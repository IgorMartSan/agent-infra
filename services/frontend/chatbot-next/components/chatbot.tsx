"use client"

import { type FormEvent, useEffect, useRef, useState } from "react"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Message } from "@/types/chat"

const defaultApiBaseUrl = "http://192.168.15.15:8000"
const apiBaseUrl = process.env.NEXT_PUBLIC_CHAT_SEND_URL ?? defaultApiBaseUrl
const defaultUserId = "user-1"
const defaultChatId = "chat-1"
const defaultAgentId = "agent1"

function createId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID()
  }

  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function Chatbot() {
  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Ola! Envie uma mensagem para iniciar a conversa.",
    },
  ])
  const [input, setInput] = useState("")
  const [userId, setUserId] = useState(defaultUserId)
  const [chatId, setChatId] = useState(defaultChatId)
  const [agentId, setAgentId] = useState(defaultAgentId)
  const [isSending, setIsSending] = useState(false)

  useEffect(() => {
    if (!apiBaseUrl) {
      return
    }

    const selectedUserId = userId.trim() || defaultUserId
    const selectedChatId = chatId.trim() || defaultChatId
    const streamUrl = `${apiBaseUrl}/users/${encodeURIComponent(selectedUserId)}/chats/${encodeURIComponent(selectedChatId)}/stream`
    const eventSource = new EventSource(streamUrl)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as {
          user_id?: string
          chat_id?: string
          response?: string
        }

        if (
          data.user_id !== selectedUserId ||
          data.chat_id !== selectedChatId ||
          typeof data.response !== "string" ||
          !data.response.trim()
        ) {
          return
        }

        const response = data.response

        setMessages((current) => [
          ...current,
          {
            id: createId(),
            role: "assistant",
            content: response,
          },
        ])
      } catch {
        return
      }
    }

    return () => {
      eventSource.close()
    }
  }, [chatId, userId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const content = input.trim()
    const selectedUserId = userId.trim() || defaultUserId
    const selectedChatId = chatId.trim() || defaultChatId
    const selectedAgentId = agentId.trim()

    if (!content || isSending) {
      return
    }

    const userMessage: Message = {
      id: createId(),
      role: "user",
      content,
    }

    setMessages((current) => [...current, userMessage])
    setInput("")
    setIsSending(true)

    if (!apiBaseUrl) {
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: "A variavel NEXT_PUBLIC_CHAT_SEND_URL nao foi configurada.",
        },
      ])
      setIsSending(false)
      return
    }

    try {
      const sendUrl = `${apiBaseUrl}/users/${encodeURIComponent(selectedUserId)}/chats/${encodeURIComponent(selectedChatId)}/messages`
      const response = await fetch(sendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: content,
          ...(selectedAgentId ? { agent_id: selectedAgentId } : {}),
        }),
      })

      if (!response.ok) {
        let errorMessage = `Erro ${response.status} ao enviar a mensagem.`

        try {
          const data = (await response.json()) as { detail?: string; message?: string }

          if (typeof data.detail === "string" && data.detail.trim()) {
            errorMessage = `${errorMessage} ${data.detail}`
          } else if (typeof data.message === "string" && data.message.trim()) {
            errorMessage = `${errorMessage} ${data.message}`
          }
        } catch {
          // Mantem a mensagem padrao.
        }

        throw new Error(errorMessage)
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Nao foi possivel enviar a mensagem. Tente novamente."

      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "assistant",
          content: errorMessage,
        },
      ])
    } finally {
      setIsSending(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/30 p-4 sm:p-6">
      <Card className="flex h-[calc(100svh-2rem)] w-full max-w-4xl border-border/60 shadow-sm sm:h-[calc(100svh-3rem)]">
        <CardHeader className="border-b">
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1">
              <CardTitle>Chatbot</CardTitle>
              <p className="text-sm text-muted-foreground">
                Chat simples conectado em {apiBaseUrl}.
              </p>
            </div>
            <Badge variant={isSending ? "default" : "secondary"}>
              {isSending ? "Enviando" : "Online"}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="flex min-h-0 flex-1 px-0">
          <ScrollArea className="h-full w-full px-4 sm:px-6">
            <div className="flex min-h-full flex-col gap-4 py-4">
              {messages.map((message) => {
                const isUser = message.role === "user"

                return (
                  <div
                    key={message.id}
                    className={`flex items-end gap-3 ${
                      isUser ? "justify-end" : "justify-start"
                    }`}
                  >
                    {!isUser && (
                      <Avatar size="sm">
                        <AvatarFallback>AI</AvatarFallback>
                      </Avatar>
                    )}

                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm sm:max-w-[75%] ${
                        isUser
                          ? "rounded-br-md bg-primary text-primary-foreground"
                          : "rounded-bl-md bg-muted text-foreground"
                      }`}
                    >
                      {message.content}
                    </div>

                    {isUser && (
                      <Avatar size="sm">
                        <AvatarFallback>VO</AvatarFallback>
                      </Avatar>
                    )}
                  </div>
                )
              })}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </CardContent>

        <CardFooter>
          <form className="flex w-full flex-col gap-3" onSubmit={handleSubmit}>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="user-id">Usuário</Label>
                <Input
                  id="user-id"
                  value={userId}
                  onChange={(event) => setUserId(event.target.value)}
                  placeholder={defaultUserId}
                  disabled={isSending}
                  autoComplete="off"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="chat-id">Chat</Label>
                <Input
                  id="chat-id"
                  value={chatId}
                  onChange={(event) => setChatId(event.target.value)}
                  placeholder={defaultChatId}
                  disabled={isSending}
                  autoComplete="off"
                />
              </div>

              <div className="space-y-1">
                <Label htmlFor="agent-id">Agente</Label>
                <Input
                  id="agent-id"
                  value={agentId}
                  onChange={(event) => setAgentId(event.target.value)}
                  placeholder={defaultAgentId}
                  list="available-agents"
                  disabled={isSending}
                  autoComplete="off"
                />
                <datalist id="available-agents">
                  <option value="agent1" />
                  <option value="agent2" />
                </datalist>
              </div>
            </div>

            <div className="flex gap-2">
              <Input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Digite sua mensagem..."
                disabled={isSending}
                autoComplete="off"
              />
              <Button type="submit" disabled={isSending || !input.trim()}>
                Enviar
              </Button>
            </div>
          </form>
        </CardFooter>
      </Card>
    </main>
  )
}
