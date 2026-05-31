import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    audit,
    config_status,
    health,
    human_review,
    incidents,
    messages_test,
    telegram,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Hermes Pest Control System",
    version="0.1.0",
    description="Channel-agnostic operational backend for pest control intake.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(config_status.router)
app.include_router(audit.router)
app.include_router(human_review.router)
app.include_router(incidents.router)
app.include_router(messages_test.router)
app.include_router(telegram.router)
