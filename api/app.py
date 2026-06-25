"""FastAPI app factory. Localhost only; CORS limited to the local Next.js dev origin."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import build_router

def create_app(settings) -> FastAPI:
    app = FastAPI(title="Value Bets API", docs_url="/api/docs")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(build_router(settings))
    return app

def serve(settings) -> None:
    import uvicorn
    uvicorn.run(create_app(settings), host="127.0.0.1", port=8000)
