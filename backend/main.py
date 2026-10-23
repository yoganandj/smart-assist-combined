"""
TPF Assistant — FastAPI backend.

Exposes:
  POST /login
  POST /chat
  GET  /health

Also serves the Angular frontend from the "static" folder.
"""

import logging
import os
import json

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent_client import FoundryAgentError, FoundryAgentService
from auth import create_access_token, require_auth
from config import get_settings
from models import (
    ChatRequest,
    ChatResponse,
    LoginRequest,
    LoginResponse,
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

STATIC_DIR = "static"

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

# ---------------------------------------------------------
# API Routes
# ---------------------------------------------------------

@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "agent_configured": agent_service.is_configured,
    }


@app.post("/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest):

    passcode = (payload.passcode or "").strip()

    if len(passcode) != 10 or not passcode.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passcode must be exactly 10 digits.",
        )

    if passcode != settings.demo_passcode:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid passcode. Please try again.",
        )

    token = create_access_token(
        subject="demo-user",
        settings=settings,
    )

    return LoginResponse(
        success=True,
        message="Login successful.",
        token=token,
    )


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
def chat(
    payload: ChatRequest,
    _user: str = Depends(require_auth),
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
        _user: str = Depends(require_auth),
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
    path = os.path.join(STATIC_DIR, "favicon.ico")
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

    requested = os.path.join(STATIC_DIR, full_path)

    if os.path.isfile(requested):
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