API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
DEFAULT_PORT = 8000
ALLOWED_EXTENSIONS = {".txt", ".md", ".docx"}
BINARY_FORMATS = {".docx"}
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
]
APP_VERSION = "1.1.1"
