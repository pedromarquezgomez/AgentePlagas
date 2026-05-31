from app.config.settings import Settings
from app.services.firestore_factory import get_firestore_service
from app.services.mock_firestore_service import MockFirestoreService


def test_firestore_factory_returns_mock_in_test_environment() -> None:
    service = get_firestore_service(
        Settings(
            app_env="test",
            firebase_credentials_path="/tmp/non-existent-service-account.json",
        )
    )

    assert isinstance(service, MockFirestoreService)


def test_firestore_factory_reuses_mock_in_test_environment() -> None:
    settings = Settings(app_env="test")

    first_service = get_firestore_service(settings)
    second_service = get_firestore_service(settings)

    assert first_service is second_service
