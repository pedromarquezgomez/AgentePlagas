from app.config.settings import Settings
from app.services.firestore_service import FirestoreService
from app.services.mock_firestore_service import MockFirestoreService


def get_firestore_service(
    settings: Settings | None = None,
) -> FirestoreService | MockFirestoreService:
    current_settings = settings or Settings()

    if current_settings.app_env == "test":
        return MockFirestoreService()

    has_explicit_firestore_config = any(
        [
            current_settings.use_firestore_emulator,
            current_settings.firebase_credentials_path,
            current_settings.firebase_credentials_json,
        ]
    )
    if has_explicit_firestore_config:
        return FirestoreService(current_settings)

    if current_settings.app_env == "development":
        return MockFirestoreService()

    return FirestoreService(current_settings)
