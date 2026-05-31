#!/usr/bin/env python3
from __future__ import annotations

import asyncio
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse

app = FastAPI(
    title="Fake Hermes Agent",
    description="Development-only HTTP stub compatible with HermesRealClient.",
)


@app.post("/agent")
async def agent(payload: dict[str, Any]):
    message = payload.get("message") or {}
    text = (message.get("text") or "").casefold()

    if "fake_invalid_json" in text:
        return PlainTextResponse("not-json", media_type="text/plain")

    if "fake_invalid_contract" in text:
        return {"reply": "Respuesta incompleta"}

    if "fake_error" in text:
        raise HTTPException(status_code=500, detail="Simulated Hermes error.")

    if "fake_timeout" in text:
        await asyncio.sleep(65)

    if _requires_human_review(text):
        return {
            "reply": (
                "Gracias por avisarnos. Por seguridad, he dejado el caso para que "
                "el equipo lo revise directamente."
            ),
            "action": {"type": "escalate_to_human", "missing_fields": []},
            "incident": {
                "should_create": True,
                "pest_type": _extract_pest_type(text),
                "location": _extract_location(text),
                "affected_area": _extract_affected_area(text),
                "priority": "urgent" if _is_urgent_review(text) else "high",
                "summary": "Caso sensible o de seguridad que requiere revisión humana.",
            },
        }

    pest_type = _extract_pest_type(text)
    affected_area = _extract_affected_area(text)
    location = _extract_location(text)

    missing_fields = []
    if not pest_type:
        missing_fields.append("pest_type")
    if not affected_area:
        missing_fields.append("affected_area")
    if not location:
        missing_fields.append("location")

    if missing_fields:
        return {
            "reply": _build_missing_data_reply(missing_fields),
            "action": {
                "type": "collect_missing_data",
                "missing_fields": missing_fields,
            },
            "incident": {"should_create": False},
        }

    return {
        "reply": (
            "Gracias por la información. He registrado el aviso para que el "
            "equipo lo revise."
        ),
        "action": {"type": "create_incident", "missing_fields": []},
        "incident": {
            "should_create": True,
            "pest_type": pest_type,
            "location": location,
            "affected_area": affected_area,
            "priority": "high" if pest_type in {"cucarachas", "roedores"} else "medium",
            "summary": (
                f"Cliente informa de presencia de {pest_type} en "
                f"{affected_area} en {location}."
            ),
        },
    }


def _requires_human_review(text: str) -> bool:
    return any(
        term in text
        for term in [
            "intoxic",
            "he respirado",
            "mareo",
            "urgencias",
            "mascota",
            "perro",
            "gato",
            "restaurante",
            "bar",
            "negocio alimentario",
            "industria alimentaria",
            "denuncia",
            "reclamación",
            "reclamacion",
            "muy enfadado",
            "producto químico",
            "producto quimico",
            "mezclar",
            "lejía",
            "lejia",
            "amoniaco",
            "garantía total",
            "garantia total",
            "precio cerrado",
        ]
    )


def _is_urgent_review(text: str) -> bool:
    return any(
        term in text
        for term in [
            "intoxic",
            "he respirado",
            "mareo",
            "urgencias",
            "mascota",
            "perro",
            "gato",
            "negocio alimentario",
            "industria alimentaria",
            "restaurante",
            "bar",
        ]
    )


def _extract_pest_type(text: str) -> str | None:
    if any(term in text for term in ["cucaracha", "cucarachas"]):
        return "cucarachas"
    if any(term in text for term in ["hormiga", "hormigas"]):
        return "hormigas"
    if any(
        term in text
        for term in [
            "roedor",
            "roedores",
            "rata",
            "ratas",
            "ratón",
            "raton",
            "ratones",
        ]
    ):
        return "roedores"
    return None


def _extract_affected_area(text: str) -> str | None:
    for area in [
        "cocina",
        "garaje",
        "baño",
        "bano",
        "jardín",
        "jardin",
        "almacén",
        "almacen",
    ]:
        if area in text:
            if area == "bano":
                return "baño"
            if area == "jardin":
                return "jardín"
            if area == "almacen":
                return "almacén"
            return area
    return None


def _extract_location(text: str) -> str | None:
    locations = {
        "torremolinos": "Torremolinos",
        "málaga": "Málaga",
        "malaga": "Málaga",
        "marbella": "Marbella",
        "fuengirola": "Fuengirola",
        "benalmádena": "Benalmádena",
        "benalmadena": "Benalmádena",
    }
    for raw, normalized in locations.items():
        if raw in text:
            return normalized
    return None


def _build_missing_data_reply(missing_fields: list[str]) -> str:
    prompts = {
        "pest_type": "qué tipo de plaga has visto",
        "affected_area": "en qué zona del inmueble está ocurriendo",
        "location": "en qué localidad se encuentra el aviso",
    }
    requested = [prompts[field] for field in missing_fields]

    if len(requested) == 1:
        details = requested[0]
    else:
        details = ", ".join(requested[:-1]) + f" y {requested[-1]}"

    return f"Para registrar el aviso necesito saber {details}."


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
