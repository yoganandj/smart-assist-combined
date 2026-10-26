"""
TPF Assistant — FastAPI backend.

Exposes:
  GET  /auth/me
  POST /chat
  POST /chat/stream
  GET  /health

Also serves the built Angular frontend from frontend/dist when available.
"""

import logging
import os
import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent_client import FoundryAgentError, FoundryAgentService
from auth import AuthenticatedUser, require_app_role
from config import get_settings
from models import (
    ChatRequest,
    ChatResponse,
    CurrentUserResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tpf.api")

settings = get_settings()
agent_service = FoundryAgentService(settings)

app = FastAPI(
    title="TPF Assistant API",
    description="Backend for the Copilot-inspired TPF Assistant POC.",
    version="1.0.0",
)

# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Serve Angular Static Files
# ---------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
_STATIC_CANDIDATES = (
    APP_DIR / "frontend" / "dist" / "frontend" / "browser",
    APP_DIR.parent / "frontend" / "dist" / "frontend" / "browser",
)
STATIC_DIR = next(
    (candidate for candidate in _STATIC_CANDIDATES if candidate.is_dir()),
    _STATIC_CANDIDATES[0],
)

if os.path.isdir(STATIC_DIR):
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "agent_configured": agent_service.is_configured,
    }


@app.get("/auth/me", response_model=CurrentUserResponse, tags=["auth"])
def current_user(user: AuthenticatedUser = Depends(require_app_role)):
    return CurrentUserResponse(
        userId=user.user_id,
        displayName=user.display_name,
        roles=list(user.roles),
    )


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(
    payload: ChatRequest,
    _user: AuthenticatedUser = Depends(require_app_role),
):

    message = (payload.message or "").strip()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty.",
        )

    try:
        reply = agent_service.get_reply(
            message,
            payload.history,
            mode=payload.mode,
        )

    except FoundryAgentError as exc:
        logger.error("Chat failed: %s", exc)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return ChatResponse(reply=reply)

@app.post("/chat/stream", tags=["chat"])
def chat_stream(
        payload: ChatRequest,
        _user: AuthenticatedUser = Depends(require_app_role),
    ) -> StreamingResponse:
        """Stream assistant responses as Server-Sent Events."""

        message = (payload.message or "").strip()

        if not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty.",
            )

        def encode_sse(event: str, data: dict[str, str]) -> str:
            return (
                f"event: {event}\n"
                f"data: {json.dumps(data)}\n\n"
            )

        def event_stream():
            try:
                for delta in agent_service.stream_reply(
                    message,
                    payload.history,
                    mode=payload.mode,
                ):
                    yield encode_sse(
                        "delta",
                        {"delta": delta},
                    )

                yield encode_sse(
                    "done",
                    {"status": "ok"},
                )

            except FoundryAgentError as exc:

                logger.error(
                    "Streaming chat failed: %s",
                    exc,
                )

                yield encode_sse(
                    "error",
                    {"detail": str(exc)},
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

# ---------------------------------------------------------
# Serve Angular files
# ---------------------------------------------------------

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    path = STATIC_DIR / "favicon.ico"
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404)


@app.get("/", include_in_schema=False)
def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "detail": "TPF Assistant API is running. Frontend build not deployed."}


@app.get("/{full_path:path}", include_in_schema=False)
def angular_routes(full_path: str):
    static_root = STATIC_DIR.resolve()
    requested = (static_root / full_path).resolve()
    if requested.is_relative_to(static_root) and requested.is_file():
        return FileResponse(requested)

    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )