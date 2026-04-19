import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_PREFIX, CORS_ORIGINS, get_app_version
from .router import router


def _configure_logging():
    """Set up logging to a file in the user's home directory."""
    log_dir = Path.home() / ".pii-washer"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "pii-washer.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return log_file


_log_file = _configure_logging()
logger = logging.getLogger("pii_washer")


def create_app(session_manager=None) -> FastAPI:
    """Create and configure the FastAPI application.

    Parameters:
        session_manager: Optional pre-built SessionManager. When provided,
            it is used directly (useful for testing). When None, a new
            SessionManager is created on startup and cleared on shutdown.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if session_manager is not None:
            app.state.session_manager = session_manager
        else:
            from pii_washer.session_manager import SessionManager
            app.state.session_manager = SessionManager()

        logger.info("PII Washer %s started (log: %s)", get_app_version(), _log_file)
        yield

        app.state.session_manager.reset()
        logger.info("PII Washer shut down, sessions cleared")

    app = FastAPI(
        title="PII Washer API",
        version=get_app_version(),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.include_router(router, prefix=API_PREFIX)

    return app


app = create_app()
