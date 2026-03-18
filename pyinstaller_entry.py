"""Entry point for the PyInstaller-bundled PII Washer desktop app.

Starts FastAPI in a background thread, then opens a native desktop
window via pywebview. Closing the window shuts everything down.
"""

import os
import sys
import threading
from pathlib import Path

import uvicorn
import webview
from starlette.responses import FileResponse

from pii_washer.api.main import create_app

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _base_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _find_ui_dir():
    """Locate the bundled UI dist directory."""
    ui_dir = os.path.join(_base_dir(), "ui")
    if os.path.isdir(ui_dir):
        return ui_dir
    return None


def _find_icon():
    """Locate the bundled app icon."""
    icon = os.path.join(_base_dir(), "icon", "pii-washer-app-icon.ico")
    if os.path.isfile(icon):
        return icon
    # Fallback for dev mode
    icon = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "app-icons", "pii-washer-app-icon.ico")
    if os.path.isfile(icon):
        return icon
    return None


def _build_app():
    app = create_app()

    ui_dir = _find_ui_dir()
    if ui_dir:
        index_html = os.path.join(ui_dir, "index.html")

        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            file_path = Path(os.path.realpath(os.path.join(ui_dir, path)))
            if path and file_path.is_relative_to(os.path.realpath(ui_dir)) and file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(index_html)

    return app


def _start_server(app):
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def main():
    app = _build_app()

    server_thread = threading.Thread(target=_start_server, args=(app,), daemon=True)
    server_thread.start()

    icon = _find_icon()
    webview.create_window("PII Washer", URL, width=1200, height=850)
    webview.start(icon=icon)


if __name__ == "__main__":
    main()
