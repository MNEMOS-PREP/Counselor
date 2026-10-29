"""M16 — Counselor, on its reserved port 8116 (PORTS.txt).

.venv\\Scripts\\python -m uvicorn backend_M16_Counselor.app:app --port 8116
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from ai_core.dependencies import DependencyRegistry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlmodel import Session, select

from . import config, counselors, db
from .llm import get_llm
from .models import Episode
from .router import router

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    get_llm()  # says once, at start, whether the words come from a model
    yield


app = FastAPI(title="M16 — Counselor", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5216", "http://127.0.0.1:5216", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health", tags=["ops"])
def health() -> dict:
    with Session(db.engine) as session:
        return {
            "status": "ok",
            "module": "M16",
            "counselors": len(counselors.all_counselors()),
            "talks": session.exec(select(func.count()).select_from(Episode)).one(),
            "words_by": "model" if get_llm().available else "template",
        }


@app.get("/v1/deps", tags=["ops"])
def deps() -> list:
    """What M16 degrades without (the platform's shape)."""
    if not config.MODULE_JSON.exists():
        return []
    return DependencyRegistry.from_manifest(config.MODULE_JSON).statuses()
