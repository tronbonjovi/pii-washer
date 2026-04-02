"""Check for application updates via GitHub Releases API."""

import inspect
import logging
from importlib.metadata import version

import httpx
from packaging.version import Version

logger = logging.getLogger(__name__)

GITHUB_REPO = "tronbonjovi/pii-washer"
GITHUB_API_URL = (
    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
)


def get_current_version() -> str:
    """Read the installed package version from metadata."""
    return version("pii-washer")


async def check_for_updates() -> dict:
    """Compare local version against the latest GitHub release.

    Returns a dict matching UpdateCheckResponse fields.
    Always succeeds (errors are returned in the response, not raised).
    """
    current = get_current_version()

    try:
        client = httpx.AsyncClient()
        resp = await client.get(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=10.0,
        )

        # Support both real httpx (sync json) and test mocks (async json)
        json_result = resp.json()
        data = await json_result if inspect.isawaitable(json_result) else json_result

        tag = data.get("tag_name")
        if not tag:
            return {
                "current_version": current,
                "latest_version": None,
                "update_available": False,
                "error": "No version tag in GitHub response",
            }

        latest = tag.lstrip("v")
        update_available = Version(latest) > Version(current)

        return {
            "current_version": current,
            "latest_version": latest,
            "update_available": update_available,
            "release_url": data.get("html_url") if update_available else None,
        }

    except Exception as exc:
        logger.warning("Update check failed: %s", exc)
        return {
            "current_version": current,
            "latest_version": None,
            "update_available": False,
            "error": "Could not reach GitHub",
        }
