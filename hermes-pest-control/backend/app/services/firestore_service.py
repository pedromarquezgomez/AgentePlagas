import json
import os
from typing import Any

from app.config.settings import Settings


class FirestoreServiceError(RuntimeError):
    pass


class FirestoreService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.client = self._build_client()

    async def create_document(
        self,
        collection: str,
        data: Any,
        document_id: str | None = None,
    ) -> dict[str, Any]:
        try:
            from google.cloud import firestore

            payload = self._to_dict(data)
            collection_ref = self.client.collection(collection)

            if document_id:
                document_ref = collection_ref.document(str(document_id))
            elif payload.get("id"):
                document_ref = collection_ref.document(str(payload["id"]))
            else:
                document_ref = collection_ref.document()

            payload["id"] = document_ref.id
            payload.setdefault("created_at", firestore.SERVER_TIMESTAMP)
            payload.setdefault("updated_at", firestore.SERVER_TIMESTAMP)
            document_ref.set(payload)
            return payload
        except Exception as exc:
            raise FirestoreServiceError(
                f"Could not create document in collection '{collection}'."
            ) from exc

    async def get_document(
        self,
        collection: str,
        document_id: str,
    ) -> dict[str, Any] | None:
        try:
            snapshot = self.client.collection(collection).document(str(document_id)).get()
            if not snapshot.exists:
                return None

            document = snapshot.to_dict() or {}
            document["id"] = snapshot.id
            return document
        except Exception as exc:
            raise FirestoreServiceError(
                f"Could not get document '{document_id}' from collection '{collection}'."
            ) from exc

    async def update_document(
        self,
        collection: str,
        document_id: str,
        data: Any,
    ) -> dict[str, Any]:
        try:
            from google.cloud import firestore

            payload = self._to_dict(data)
            payload["id"] = str(document_id)
            payload["updated_at"] = firestore.SERVER_TIMESTAMP
            self.client.collection(collection).document(str(document_id)).set(
                payload,
                merge=True,
            )
            return payload
        except Exception as exc:
            raise FirestoreServiceError(
                f"Could not update document '{document_id}' in collection '{collection}'."
            ) from exc

    async def list_documents(
        self,
        collection: str,
        filters: dict[str, Any] | list[tuple[str, str, Any]] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        try:
            query = self.client.collection(collection)

            if isinstance(filters, dict):
                for field, value in filters.items():
                    query = query.where(field, "==", value)
            elif filters:
                for field, operator, value in filters:
                    query = query.where(field, operator, value)

            if limit is not None:
                query = query.limit(limit)

            documents = []
            for snapshot in query.stream():
                document = snapshot.to_dict() or {}
                document["id"] = snapshot.id
                documents.append(document)
            return documents
        except Exception as exc:
            raise FirestoreServiceError(
                f"Could not list documents from collection '{collection}'."
            ) from exc

    async def append_to_subcollection(
        self,
        parent_collection: str,
        parent_id: str,
        subcollection: str,
        data: Any,
    ) -> dict[str, Any]:
        try:
            from google.cloud import firestore

            payload = self._to_dict(data)
            document_ref = (
                self.client.collection(parent_collection)
                .document(str(parent_id))
                .collection(subcollection)
                .document()
            )
            payload["id"] = document_ref.id
            payload.setdefault("created_at", firestore.SERVER_TIMESTAMP)
            document_ref.set(payload)
            return payload
        except Exception as exc:
            raise FirestoreServiceError(
                "Could not append document to subcollection "
                f"'{parent_collection}/{parent_id}/{subcollection}'."
            ) from exc

    def _build_client(self) -> Any:
        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if self.settings.use_firestore_emulator:
                if self.settings.firestore_emulator_host:
                    os.environ["FIRESTORE_EMULATOR_HOST"] = (
                        self.settings.firestore_emulator_host
                    )
                self._initialize_app(firebase_admin)
                return firestore.client()

            if self.settings.firebase_credentials_path:
                certificate = credentials.Certificate(
                    self.settings.firebase_credentials_path
                )
                self._initialize_app(firebase_admin, certificate)
                return firestore.client()

            if self.settings.firebase_credentials_json:
                certificate_data = json.loads(self.settings.firebase_credentials_json)
                certificate = credentials.Certificate(certificate_data)
                self._initialize_app(firebase_admin, certificate)
                return firestore.client()

            self._initialize_app(firebase_admin)
            return firestore.client()
        except Exception as exc:
            raise FirestoreServiceError("Could not initialize Firebase Firestore.") from exc

    def _initialize_app(
        self,
        firebase_admin_module: Any,
        credential: Any | None = None,
    ) -> None:
        if firebase_admin_module._apps:
            return

        options = {}
        if self.settings.firebase_project_id:
            options["projectId"] = self.settings.firebase_project_id

        if credential is not None:
            firebase_admin_module.initialize_app(credential, options=options or None)
        else:
            firebase_admin_module.initialize_app(options=options or None)

    def _to_dict(self, data: Any) -> dict[str, Any]:
        if hasattr(data, "model_dump"):
            return data.model_dump()
        if isinstance(data, dict):
            return dict(data)
        raise FirestoreServiceError(
            f"Firestore data must be a dict or Pydantic model, got {type(data)!r}."
        )
