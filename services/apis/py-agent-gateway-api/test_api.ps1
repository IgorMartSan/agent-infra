$body = @{
    application_id = "test-app"
    user_id = "user-123"
    chat_id = "chat-456"
    agent_id = "agent-suporte"
    message = "Teste de mensagem"
    metadata = @{ source = "test" }
} | ConvertTo-Json

Write-Host "Enviando requisição para http://localhost:8000/api/v1/messages..."
$result = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/messages" -Method Post -Body $body -ContentType "application/json"
Write-Host "Resposta:"
$result | ConvertTo-Json