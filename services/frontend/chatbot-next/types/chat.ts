export type Message = {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  createdAt?: string
  messageId?: string
  status?: "accepted" | "error"
}
