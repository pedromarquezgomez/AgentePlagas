from app.config.settings import Settings
from app.services.firestore_service import FirestoreService
from app.services.mock_firestore_service import MockFirestoreService

_mock_firestore_service: MockFirestoreService | None = None


class FirestoreConfigurationError(RuntimeError):
    pass


def get_firestore_service(
    settings: Settings | None = None,
) -> FirestoreService | MockFirestoreService:
    current_settings = settings or Settings()

    if current_settings.app_env == "test":
        return _get_mock_firestore_service()

    if has_firestore_real_config(current_settings):
        return FirestoreService(current_settings)

    if current_settings.app_env == "development":
        return _get_mock_firestore_service()

    if current_settings.app_env == "production":
        raise FirestoreConfigurationError(
            "Firestore credentials are required when APP_ENV=production. "
            "Set FIREBASE_CREDENTIALS_PATH, FIREBASE_CREDENTIALS_JSON, or "
            "USE_FIRESTORE_EMULATOR=true for non-production verification."
        )

    return FirestoreService(current_settings)


def has_firestore_real_config(settings: Settings) -> bool:
    return bool(
        settings.use_firestore_emulator
        or settings.firebase_credentials_path
        or settings.firebase_credentials_json
        or (settings.app_env == "production" and settings.firebase_project_id)
    )


def has_firestore_credentials(settings: Settings) -> bool:
    return bool(settings.firebase_credentials_path or settings.firebase_credentials_json)


def _get_mock_firestore_service() -> MockFirestoreService:
    global _mock_firestore_service
    if _mock_firestore_service is None:
        _mock_firestore_service = MockFirestoreService()
        from app.services.mock_seeder import seed_mock_data
        seed_mock_data(_mock_firestore_service)
    return _mock_firestore_service
