"use client"

import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from "react"
import {
  Bot,
  Check,
  ChevronDown,
  CircleAlert,
  LoaderCircle,
  MessageSquarePlus,
  Send,
  Settings2,
  UserRound,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import type { Message } from "@/types/chat"

const defaultApplicationId = "chatbot-next"
const defaultUserId = "user-1"
const defaultAgentId = "gemma4-agent"

const suggestions = [
  "Olá! Quem é você?",
  "Explique como este agente funciona.",
  "Faça um resumo desta conversa.",
]

function createId() {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID()
  }

  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function createChatId() {
  return `chat-${Date.now().toString(36)}`
}

function currentTime() {
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date())
}

type ApiStatus = "checking" | "online" | "offline"

export function Chatbot() {
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const receivedMessageIdsRef = useRef(new Set<string>())

  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Olá! Este é o playground do agente. Envie uma mensagem para testar o fluxo completo.",
    },
  ])
  const [input, setInput] = useState("")
  const [applicationId, setApplicationId] = useState(defaultApplicationId)
  const [userId, setUserId] = useState(defaultUserId)
  const [chatId, setChatId] = useState("chat-1")
  const [agentId, setAgentId] = useState(defaultAgentId)
  const [isSending, setIsSending] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [apiStatus, setApiStatus] = useState<ApiStatus>("checking")
  const [streamConnected, setStreamConnected] = useState(false)

  useEffect(() => {
    const controller = new AbortController()

    async function checkApi() {
      try {
        const response = await fetch("/api/chat", {
          cache: "no-store",
          signal: controller.signal,
        })
        setApiStatus(response.ok ? "online" : "offline")
      } catch {
        if (!controller.signal.aborted) setApiStatus("offline")
      }
    }

    void checkApi()
    return () => controller.abort()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isSending])

  useEffect(() => {
    const selectedApplicationId = applicationId.trim() || defaultApplicationId
    const selectedChatId = chatId.trim() || "chat-1"
    const params = new URLSearchParams({
      application_id: selectedApplicationId,
      chat_id: selectedChatId,
    })
    const eventSource = new EventSource(`/api/chat/stream?${params}`)

    eventSource.onopen = () => setStreamConnected(true)
    eventSource.onerror = () => setStreamConnected(false)
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as {
          type?: string
          application_id?: string
          conversation_id?: string
          message_id?: string
          content?: string
          response?: string
        }
        const content = data.content ?? data.response

        if (!content?.trim()) return
        if (
          data.message_id &&
          receivedMessageIdsRef.current.has(data.message_id)
        ) {
          return
        }
        if (data.message_id) receivedMessageIdsRef.current.add(data.message_id)

        setMessages((current) => [
          ...current,
          {
            id: data.message_id || createId(),
            role: "assistant",
            content,
            createdAt: currentTime(),
          },
        ])
      } catch {
        // Ignora eventos que não seguem o contrato de resposta do agente.
      }
    }

    return () => eventSource.close()
  }, [applicationId, chatId])

  async function sendMessage(content: string) {
    const selectedApplicationId = applicationId.trim() || defaultApplicationId
    const selectedUserId = userId.trim() || defaultUserId
    const selectedChatId = chatId.trim() || createChatId()
    const selectedAgentId = agentId.trim() || defaultAgentId

    setMessages((current) => [
      ...current,
      {
        id: createId(),
        role: "user",
        content,
        createdAt: currentTime(),
      },
    ])
    setInput("")
    setIsSending(true)

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          application_id: selectedApplicationId,
          user_id: selectedUserId,
          chat_id: selectedChatId,
          agent_id: selectedAgentId,
          message: content,
          metadata: { source: "chatbot-next" },
          delivery: { type: "NONE" },
        }),
      })

      const data = (await response.json()) as {
        detail?: string
        message_id?: string
      }

      if (!response.ok) {
        throw new Error(
          data.detail || `A API retornou o erro ${response.status}.`
        )
      }

      setApiStatus("online")
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "system",
          content:
            "Mensagem aceita pelo gateway e encaminhada para processamento.",
          createdAt: currentTime(),
          messageId: data.message_id,
          status: "accepted",
        },
      ])
    } catch (error) {
      setApiStatus("offline")
      setMessages((current) => [
        ...current,
        {
          id: createId(),
          role: "system",
          content:
            error instanceof Error
              ? error.message
              : "Não foi possível enviar a mensagem. Tente novamente.",
          createdAt: currentTime(),
          status: "error",
        },
      ])
    } finally {
      setIsSending(false)
      window.setTimeout(() => textareaRef.current?.focus(), 0)
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const content = input.trim()

    if (!content || isSending) return
    void sendMessage(content)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  function startNewChat() {
    setChatId(createChatId())
    setMessages([
      {
        id: createId(),
        role: "assistant",
        content: "Nova conversa iniciada. O que você quer testar?",
        createdAt: currentTime(),
      },
    ])
    window.setTimeout(() => textareaRef.current?.focus(), 0)
  }

  const statusLabel =
    apiStatus === "offline"
      ? "API indisponível"
      : streamConnected
        ? "Retorno conectado"
        : apiStatus === "checking"
          ? "Verificando API"
          : "Conectando retorno"

  return (
    <main className="chat-shell">
      <section className="chat-panel" aria-label="Playground do agente">
        <header className="chat-header">
          <div className="flex min-w-0 items-center gap-3">
            <div className="agent-mark" aria-hidden="true">
              <Bot className="size-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg">
                  Agent Playground
                </h1>
                <Badge
                  variant={
                    apiStatus === "offline" ? "destructive" : "secondary"
                  }
                  className="hidden sm:inline-flex"
                >
                  <span
                    className={`size-1.5 rounded-full ${
                      apiStatus === "online" && streamConnected
                        ? "bg-emerald-500"
                        : apiStatus === "checking"
                          ? "animate-pulse bg-amber-500"
                          : "bg-red-500"
                    }`}
                  />
                  {statusLabel}
                </Badge>
              </div>
              <p className="truncate text-xs text-muted-foreground sm:text-sm">
                Teste o envio de mensagens para o seu agente
              </p>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={startNewChat}
          >
            <MessageSquarePlus data-icon="inline-start" />
            <span className="hidden sm:inline">Nova conversa</span>
          </Button>
        </header>

        <Collapsible open={settingsOpen} onOpenChange={setSettingsOpen}>
          <CollapsibleTrigger asChild>
            <button className="settings-trigger" type="button">
              <span className="flex min-w-0 items-center gap-2">
                <Settings2 className="size-4 shrink-0" />
                <span className="font-medium">Configuração do teste</span>
                <span className="hidden truncate text-muted-foreground sm:inline">
                  {agentId || defaultAgentId} · {chatId}
                </span>
              </span>
              <ChevronDown
                className={`size-4 shrink-0 transition-transform ${settingsOpen ? "rotate-180" : ""}`}
              />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent className="settings-content">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Field
                id="application-id"
                label="Aplicação"
                value={applicationId}
                onChange={setApplicationId}
                placeholder={defaultApplicationId}
              />
              <Field
                id="user-id"
                label="Usuário"
                value={userId}
                onChange={setUserId}
                placeholder={defaultUserId}
              />
              <Field
                id="chat-id"
                label="Conversa"
                value={chatId}
                onChange={setChatId}
                placeholder="chat-1"
              />
              <Field
                id="agent-id"
                label="Agente"
                value={agentId}
                onChange={setAgentId}
                placeholder={defaultAgentId}
                list="available-agents"
              />
              <datalist id="available-agents">
                <option value="gemma4-agent" />
                <option value="simple-agent" />
              </datalist>
            </div>
          </CollapsibleContent>
        </Collapsible>

        <ScrollArea className="min-h-0 flex-1">
          <div className="mx-auto flex min-h-full w-full max-w-3xl flex-col px-4 py-6 sm:px-8 sm:py-8">
            <div className="flex flex-1 flex-col justify-end gap-5">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              {isSending && (
                <div className="flex items-center gap-2 pl-11 text-sm text-muted-foreground">
                  <LoaderCircle className="size-4 animate-spin" />
                  Enviando para o gateway…
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </ScrollArea>

        <footer className="composer-wrap">
          <div className="mx-auto w-full max-w-3xl">
            {messages.length === 1 && (
              <div className="mb-3 flex gap-2 overflow-x-auto pb-1">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    className="suggestion-chip"
                    onClick={() => setInput(suggestion)}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            <form className="composer" onSubmit={handleSubmit}>
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Escreva uma mensagem para o agente…"
                className="max-h-36 min-h-12 resize-none border-0 bg-transparent px-3 py-3 shadow-none focus-visible:ring-0"
                disabled={isSending}
                aria-label="Mensagem"
              />
              <Button
                type="submit"
                size="icon-lg"
                className="mr-1.5 mb-1.5 rounded-xl"
                disabled={isSending || !input.trim() || !streamConnected}
                aria-label="Enviar mensagem"
              >
                {isSending ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <Send />
                )}
              </Button>
            </form>
            <p className="mt-2 text-center text-[11px] text-muted-foreground">
              Enter para enviar · Shift + Enter para quebrar linha
            </p>
          </div>
        </footer>
      </section>
    </main>
  )
}

function Field({
  id,
  label,
  value,
  onChange,
  placeholder,
  list,
}: {
  id: string
  label: string
  value: string
  onChange: (value: string) => void
  placeholder: string
  list?: string
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {label}
      </Label>
      <Input
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        list={list}
        autoComplete="off"
        className="bg-background"
      />
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === "system") {
    const isError = message.status === "error"

    return (
      <div
        className={`system-message ${isError ? "system-message-error" : ""}`}
        role={isError ? "alert" : "status"}
      >
        {isError ? (
          <CircleAlert className="mt-0.5 size-4 shrink-0" />
        ) : (
          <Check className="mt-0.5 size-4 shrink-0" />
        )}
        <div className="min-w-0">
          <p>{message.content}</p>
          {message.messageId && (
            <p className="mt-1 truncate font-mono text-[10px] opacity-70">
              ID: {message.messageId}
            </p>
          )}
        </div>
      </div>
    )
  }

  const isUser = message.role === "user"

  return (
    <article className={`message-row ${isUser ? "message-row-user" : ""}`}>
      <div className={`message-avatar ${isUser ? "message-avatar-user" : ""}`}>
        {isUser ? <UserRound /> : <Bot />}
      </div>
      <div className={`message-block ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`message-bubble ${isUser ? "message-bubble-user" : ""}`}
        >
          {message.content}
        </div>
        {message.createdAt && (
          <time className="px-1 text-[10px] text-muted-foreground">
            {message.createdAt}
          </time>
        )}
      </div>
    </article>
  )
}
