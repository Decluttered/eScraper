import pytest

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_settings_frontend_origin_has_no_trailing_slash() -> None:
    settings = get_settings()
    assert str(settings.frontend_origin) == "http://localhost:5173"


def test_settings_accepts_origin_with_trailing_slash() -> None:
    settings = Settings(frontend_origin="http://localhost:5173/")
    assert str(settings.frontend_origin) == "http://localhost:5173"


def test_settings_accepts_origin_with_path() -> None:
    settings = Settings(frontend_origin="https://app.example.com/dashboard")
    assert str(settings.frontend_origin) == "https://app.example.com/dashboard"
