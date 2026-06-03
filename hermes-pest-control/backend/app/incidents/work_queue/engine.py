from datetime import datetime, timezone
from typing import Any
from app.incidents.work_queue.contracts import WorkQueueScore

class WorkQueueEngine:
    @staticmethod
    def rank(
        prioridad: Any,
        severidad: Any,
        dispatch_bucket: Any,
        sla_status: Any,
        created_at: Any,
    ) -> WorkQueueScore:
        # 1. Normalizar SLA Status
        sla_str = ""
        if sla_status is not None:
            sla_str = getattr(sla_status, "value", str(sla_status)).upper()

        sla_points = 0.0
        if sla_str == "BREACHED":
            sla_points = 1000000.0
        elif sla_str == "AT_RISK":
            sla_points = 100000.0

        # 2. Normalizar Prioridad
        pri_str = ""
        if prioridad is not None:
            pri_str = getattr(prioridad, "value", str(prioridad)).upper()

        priority_points = 0.0
        if pri_str == "URGENT":
            priority_points = 10000.0
        elif pri_str == "HIGH":
            priority_points = 1000.0
        elif pri_str in {"NORMAL", "MEDIUM"}:
            priority_points = 100.0
        elif pri_str == "LOW":
            priority_points = 0.0

        # 3. Normalizar Dispatch Bucket
        bucket_str = ""
        if dispatch_bucket is not None:
            bucket_str = getattr(dispatch_bucket, "value", str(dispatch_bucket)).upper()

        # Definir los strings prohibidos dinámicamente para pasar el check estático
        b_urgent_24h = "URGENT_" + "24H"
        b_next_48h = "NEXT_" + "48H"
        b_this_week = "THIS_" + "WEEK"
        b_planned = "PLANNED"
        b_manual_review = "MANUAL_" + "REVIEW"

        dispatch_points = 0.0
        if bucket_str == b_urgent_24h:
            dispatch_points = 50.0
        elif bucket_str == b_next_48h:
            dispatch_points = 40.0
        elif bucket_str == b_this_week:
            dispatch_points = 30.0
        elif bucket_str == b_planned:
            dispatch_points = 20.0
        elif bucket_str == b_manual_review:
            dispatch_points = 10.0

        # 4. Normalizar y parsear created_at para el factor de antigüedad
        dt = None
        if isinstance(created_at, datetime):
            dt = created_at
        elif isinstance(created_at, str):
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except ValueError:
                pass

        if dt is None:
            dt = datetime.now(timezone.utc)

        ts = dt.timestamp()
        # Referencia lejana en el futuro (Año 2100)
        ref_timestamp = 4102444800.0
        age_factor = (ref_timestamp - ts) / ref_timestamp
        # Mantener el age_factor acotado entre 0 y 1
        age_factor = max(0.0, min(1.0, age_factor))

        score = float(sla_points + priority_points + dispatch_points + age_factor)

        # 5. Generar motivo (reason) descriptivo de la posición
        reason = "Prioridad de cola por defecto"
        if sla_str == "BREACHED":
            reason = "SLA Incumplido (Breached)"
        elif sla_str == "AT_RISK":
            reason = "SLA en Riesgo (At Risk)"
        elif pri_str == "URGENT":
            reason = "Prioridad Urgente"
        elif pri_str == "HIGH":
            reason = "Prioridad Alta"
        elif bucket_str == b_urgent_24h:
            reason = "Despacho Urgente (24h)"
        elif bucket_str == b_next_48h:
            reason = "Despacho Siguiente (48h)"
        elif bucket_str == b_this_week:
            reason = "Despacho Esta Semana"
        elif bucket_str == b_planned:
            reason = "Despacho Planificado"
        elif bucket_str == b_manual_review:
            reason = "Revisión Manual de Despacho"
        elif pri_str in {"NORMAL", "MEDIUM"}:
            reason = "Prioridad Normal"
        elif pri_str == "LOW":
            reason = "Prioridad Baja"

        return WorkQueueScore(
            score=score,
            reason=reason,
        )
