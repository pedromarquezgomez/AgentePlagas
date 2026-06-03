import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.cors import get_cors_allowed_origins
from app.config.settings import settings
from app.routes import (
    audit,
    calendar,
    config_status,
    dashboard,
    documents,
    health,
    human_review,
    incidents,
    messages_test,
    technicians,
    telegram,
    tools,
    visits,
    whatsapp,
    evaluation,
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
    allow_origins=get_cors_allowed_origins(settings),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("app.errors").exception(
        "Unhandled request error path=%s method=%s",
        request.url.path,
        request.method,
    )
    response = JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") in get_cors_allowed_origins(settings):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    return response

app.include_router(health.router)
app.include_router(config_status.router)
app.include_router(audit.router)
app.include_router(calendar.router)
app.include_router(dashboard.router)
app.include_router(documents.router)
app.include_router(human_review.router)
app.include_router(incidents.router)
app.include_router(technicians.router)
app.include_router(tools.router)
app.include_router(visits.router)
app.include_router(messages_test.router)
app.include_router(telegram.router)
app.include_router(whatsapp.router)
app.include_router(evaluation.router)
