from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import API_PREFIX, APP_VERSION, CORS_ORIGINS
from .router import router


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

        yield

        app.state.session_manager.clear_all_sessions()

    app = FastAPI(
        title="PII Washer API",
        version=APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=API_PREFIX)

    return app


app = create_app()
