from typing import Any


class HistoryBuilder:
    def __init__(self, firestore_service: Any = None) -> None:
        self.firestore_service = firestore_service

    async def build(
        self,
        conversation_id: str,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        # Si se pasa un historial de conversación explícito, lo preferimos
        if conversation_history:
            return conversation_history

        if not self.firestore_service:
            return []

        try:
            # Obtener mensajes ordenados por created_at de Firestore
            docs = await self.firestore_service.list_documents(
                "messages",
                filters={"conversation_id": conversation_id},
            )
            if not docs:
                return []

            # Ordenar por created_at de forma ascendente
            sorted_docs = sorted(docs, key=lambda x: str(x.get("created_at") or ""))
            
            history = []
            for doc in sorted_docs:
                direction = doc.get("direction")
                text = doc.get("text")
                if not text:
                    continue
                role = "user" if direction == "inbound" else "assistant"
                history.append({"role": role, "content": text})
            return history
        except Exception:
            return []
