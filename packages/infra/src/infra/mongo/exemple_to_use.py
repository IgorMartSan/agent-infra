from datetime import datetime, timezone
from pymongo import MongoClient


class MongoConnection:
    def __init__(self, uri: str = "mongodb://localhost:27017", db_name: str = "chat_db"):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

    def get_database(self):
        return self.db


if __name__ == "__main__":
    self.client = MongoClient(uri: str = "mongodb://localhost:27017")
    self.db = self.client["chat_db"]

    short_term_repository = ShortTermRepository(
        mongo_connection=mongo_connection,
        max_messages=50,
    )

    long_term_repository = LongTermRepository(
        mongo_connection=mongo_connection,
    )

    platform = "whatsapp"
    user_id = "551199999999"
    client_id = f"{platform}:{user_id}"

    mensagens_usuario = [
        "Quero automatizar boletos",
        "Uso SAP",
        "Recebo muitos emails",
        "Quero extrair dados automaticamente",
        "Preciso integrar com ERP",
        "Também quero notificações",
    ]

    for mensagem_usuario in mensagens_usuario:
        print(f"\nUSER: {mensagem_usuario}")

        # 1. salva mensagem do usuário
        short_term_repository.save(
            platform=platform,
            user_id=user_id,
            message=mensagem_usuario,
            role="user",
        )

        # 2. busca histórico recente para montar prompt
        historico = short_term_repository.get_recent(client_id=client_id, limit=10)

        # 3. busca contexto de longo prazo
        contexto = long_term_repository.get(client_id=client_id) or {}

        resumo = (
            contexto.get("contexts", {})
            .get("summary", {})
            .get("text", "")
        )

        # 4. monta prompt
        prompt = [
            {
                "role": "system",
                "content": f"Resumo do cliente: {resumo}"
            }
        ] + historico

        print("\nPROMPT ENVIADO PARA LLM:")
        for item in prompt:
            print(item)

        # 5. simula resposta da LLM
        resposta_llm = f"Resposta gerada para: {mensagem_usuario}"

        print(f"\nASSISTANT: {resposta_llm}")

        # 6. salva resposta da LLM
        short_term_repository.save(
            platform=platform,
            user_id=user_id,
            message=resposta_llm,
            role="assistant",
            metadata={
                "model": "fake-llm",
                "created_by": "test",
            },
        )

        # 7. a cada 10 mensagens totais, atualiza contexto long term
        total_mensagens = short_term_repository.count(client_id=client_id)

        if total_mensagens % 10 == 0:
            historico_para_resumo = short_term_repository.get_recent(
                client_id=client_id,
                limit=20,
            )

            textos = [item["content"] for item in historico_para_resumo]

            resumo_gerado = " | ".join(textos[-5:])

            long_term_repository.upsert_context(
                client_id=client_id,
                context_type="summary",
                data={
                    "text": resumo_gerado,
                    "updated_at": datetime.now(timezone.utc),
                    "source_count": len(historico_para_resumo),
                },
            )

            print("\nResumo atualizado no long term memory.")

    print("\n" + "=" * 60)
    print("CONTEXTO FINAL")
    print("=" * 60)
    print(long_term_repository.get(client_id=client_id))

    print("\n" + "=" * 60)
    print("ÚLTIMAS MENSAGENS")
    print("=" * 60)
    for item in short_term_repository.get_recent_raw(client_id=client_id, limit=10):
        print(item)