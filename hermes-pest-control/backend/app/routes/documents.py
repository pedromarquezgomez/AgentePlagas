from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies.admin_auth import require_admin_auth
from app.schemas.operational_document import (
    OperationalDocumentCreate,
    OperationalDocumentUpdate,
)
from app.services.incident_service import IncidentNotFoundError, IncidentService
from app.services.operational_document_service import (
    OperationalDocumentNotFoundError,
    OperationalDocumentService,
)
from app.services.technician_service import TechnicianNotFoundError, TechnicianService
from app.services.visit_service import VisitNotFoundError, VisitService

router = APIRouter(tags=["documents"], dependencies=[Depends(require_admin_auth)])
document_service = OperationalDocumentService()
incident_service = IncidentService()
visit_service = VisitService()
technician_service = TechnicianService()


@router.get("/documents")
async def list_documents(
    incident_id: str | None = None,
    visit_id: str | None = None,
    document_type: str | None = None,
    status: str | None = None,
    limit: int | None = Query(default=50, ge=1, le=200),
) -> list[dict]:
    return await document_service.list_documents(
        incident_id=incident_id,
        visit_id=visit_id,
        document_type=document_type,
        status_filter=status,
        limit=limit,
    )


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def create_document(document_create: OperationalDocumentCreate) -> dict:
    document = await document_service.create_document(document_create)
    return document.model_dump()


@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict:
    try:
        return await document_service.get_document(document_id)
    except OperationalDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    document_update: OperationalDocumentUpdate,
) -> dict:
    updates = document_update.model_dump(exclude_unset=True)
    try:
        return await document_service.update_document(document_id, updates)
    except OperationalDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc


@router.post("/incidents/{incident_id}/generate-summary-document")
async def generate_incident_summary_document(incident_id: str) -> dict:
    try:
        incident = await incident_service.get_incident(incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        ) from exc

    title = f"Resumen de incidencia {incident_id}"
    content = "\n".join(
        [
            "Resumen operativo de incidencia",
            f"Tipo de plaga: {_value(incident.get('pest_type'))}",
            f"Localidad: {_value(incident.get('location'))}",
            f"Zona afectada: {_value(incident.get('affected_area'))}",
            f"Prioridad: {_value(incident.get('priority'))}",
            f"Estado: {_value(incident.get('status'))}",
            f"Resumen: {_value(incident.get('summary'))}",
            "Nota: documento operativo interno, no certificado legal oficial.",
        ]
    )
    document = await document_service.create_document(
        OperationalDocumentCreate(
            document_type="incident_summary",
            incident_id=incident_id,
            title=title,
            content=content,
            generated_by="system",
            metadata={"generated_from": "incident_template"},
        )
    )
    return document.model_dump()


@router.post("/visits/{visit_id}/generate-technician-brief")
async def generate_technician_brief(visit_id: str) -> dict:
    try:
        visit = await visit_service.get_visit(visit_id)
    except VisitNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found.",
        ) from exc

    incident = None
    try:
        incident = await incident_service.get_incident(visit["incident_id"])
    except IncidentNotFoundError:
        incident = None

    technician = None
    if visit.get("technician_id"):
        try:
            technician = await technician_service.get_technician(visit["technician_id"])
        except TechnicianNotFoundError:
            technician = None

    title = f"Brief técnico visita {visit_id}"
    content = "\n".join(
        [
            "Brief operativo para técnico",
            f"Visita: {visit_id}",
            f"Incidencia: {_value(visit.get('incident_id'))}",
            f"Técnico: {_value(technician.get('name') if technician else visit.get('technician_id'))}",
            f"Inicio: {_value(visit.get('scheduled_start'))}",
            f"Fin: {_value(visit.get('scheduled_end'))}",
            f"Dirección: {_value(visit.get('address'))}",
            f"Tipo de plaga: {_value(incident.get('pest_type') if incident else None)}",
            f"Zona afectada: {_value(incident.get('affected_area') if incident else None)}",
            f"Notas de visita: {_value(visit.get('notes'))}",
            "Nota: documento operativo interno, no certificado legal oficial.",
        ]
    )
    document = await document_service.create_document(
        OperationalDocumentCreate(
            document_type="technician_brief",
            incident_id=visit.get("incident_id"),
            visit_id=visit_id,
            title=title,
            content=content,
            generated_by="system",
            metadata={"generated_from": "technician_brief_template"},
        )
    )
    return document.model_dump()


@router.get("/documents/{document_id}/versions")
async def list_document_versions(document_id: str) -> list[dict]:
    try:
        return await document_service.list_document_versions(document_id)
    except OperationalDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc


@router.post("/documents/{document_id}/versions", status_code=status.HTTP_201_CREATED)
async def create_document_version(
    document_id: str,
    payload: dict,
) -> dict:
    content = payload.get("content")
    generated_by = payload.get("generated_by", "admin")
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content field is required.",
        )
    try:
        return await document_service.create_document_version(
            document_id=document_id,
            content=content,
            generated_by=generated_by,
        )
    except OperationalDocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc


def _value(value: object) -> str:
    return str(value) if value not in (None, "") else "Sin dato"
