"""Tests for the update check endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from pii_washer.api.main import create_app
from pii_washer.session_manager import SessionManager


@pytest.fixture
def client():
    from pii_washer.tests.test_api import MockDetectionEngine

    manager = SessionManager(detection_engine=MockDetectionEngine())
    app = create_app(session_manager=manager)
    with TestClient(app) as c:
        yield c


GITHUB_RELEASES_URL = (
    "https://api.github.com/repos/tronbonjovi/pii-washer/releases/latest"
)


class TestUpdateCheck:
    """Tests for GET /api/v1/updates/check."""

    def test_up_to_date(self, client):
        """When local version matches GitHub, report up to date."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v1.0.1",
            "html_url": "https://github.com/tronbonjovi/pii-washer/releases/tag/v1.0.1",
        }

        with patch("pii_washer.api.update_checker.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.get("/api/v1/updates/check")

        assert r.status_code == 200
        body = r.json()
        assert body["current_version"] == "1.0.1"
        assert body["latest_version"] == "1.0.1"
        assert body["update_available"] is False
        assert body["error"] is None

    def test_update_available(self, client):
        """When GitHub has a newer version, report update available."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tag_name": "v2.0.0",
            "html_url": "https://github.com/tronbonjovi/pii-washer/releases/tag/v2.0.0",
        }

        with patch("pii_washer.api.update_checker.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.get("/api/v1/updates/check")

        assert r.status_code == 200
        body = r.json()
        assert body["current_version"] == "1.0.1"
        assert body["latest_version"] == "2.0.0"
        assert body["update_available"] is True
        assert body["release_url"] == "https://github.com/tronbonjovi/pii-washer/releases/tag/v2.0.0"

    def test_github_unreachable(self, client):
        """When GitHub is unreachable, return error gracefully."""
        with patch("pii_washer.api.update_checker.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = Exception("Connection refused")
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.get("/api/v1/updates/check")

        assert r.status_code == 200
        body = r.json()
        assert body["current_version"] == "1.0.1"
        assert body["latest_version"] is None
        assert body["update_available"] is False
        assert body["error"] is not None

    def test_malformed_github_response(self, client):
        """When GitHub returns unexpected data, handle gracefully."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected": "data"}

        with patch("pii_washer.api.update_checker.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            r = client.get("/api/v1/updates/check")

        assert r.status_code == 200
        body = r.json()
        assert body["current_version"] == "1.0.1"
        assert body["latest_version"] is None
        assert body["update_available"] is False
        assert body["error"] is not None
