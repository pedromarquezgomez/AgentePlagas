from app.config.settings import Settings
from app.services.firestore_factory import (
    FirestoreConfigurationError,
    get_firestore_service,
)
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


def test_firestore_factory_returns_mock_in_development_without_credentials() -> None:
    service = get_firestore_service(
        Settings(
            app_env="development",
            firebase_credentials_path="",
            firebase_credentials_json="",
            use_firestore_emulator=False,
        )
    )

    assert isinstance(service, MockFirestoreService)


def test_firestore_factory_fails_in_production_without_credentials() -> None:
    settings = Settings(
        app_env="production",
        firebase_credentials_path="",
        firebase_credentials_json="",
        use_firestore_emulator=False,
    )

    try:
        get_firestore_service(settings)
    except FirestoreConfigurationError as exc:
        assert "Firestore credentials are required" in str(exc)
    else:
        raise AssertionError("Expected FirestoreConfigurationError")
