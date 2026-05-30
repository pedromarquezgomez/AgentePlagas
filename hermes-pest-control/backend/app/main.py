from fastapi import FastAPI

from app.routes import health, messages_test

app = FastAPI(
    title="Hermes Pest Control System",
    version="0.1.0",
    description="Channel-agnostic operational backend for pest control intake.",
)

app.include_router(health.router)
app.include_router(messages_test.router)

