from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
DEFAULT_PORT = 8000
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".csv", ".xlsx", ".html"}
BINARY_FORMATS = {".docx", ".pdf", ".csv", ".xlsx", ".html"}
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
]


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Return the installed package version. Single source of truth: pyproject.toml."""
    try:
        return version("pii-washer")
    except PackageNotFoundError:
        return "0.0.0+unknown"
