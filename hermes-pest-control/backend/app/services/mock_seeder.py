from datetime import datetime, timedelta, timezone
from uuid import uuid4


def seed_mock_data(service) -> None:
    # Si ya hay datos de técnicos, no sobreescribir el seed
    if service._collections.get("technicians"):
        return

    print("Seeding development mock database...")

    # --- TECHNICIANS ---
    tech_pedro_id = "tech-pedro"
    tech_ana_id = "tech-ana"
    tech_luis_id = "tech-luis"

    service._collections["technicians"] = {
        tech_pedro_id: {
            "id": tech_pedro_id,
            "name": "Pedro Técnico",
            "phone": "+34666555444",
            "email": "pedro@hermes.test",
            "active": True,
            "service_area": "Fuengirola",
            "skills": ["cucarachas", "roedores"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        tech_ana_id: {
            "id": tech_ana_id,
            "name": "Ana Técnica",
            "phone": "+34666555333",
            "email": "ana@hermes.test",
            "active": True,
            "service_area": "Málaga",
            "skills": ["cucarachas", "roedores", "aves"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        tech_luis_id: {
            "id": tech_luis_id,
            "name": "Luis Técnico",
            "phone": "+34666555222",
            "email": "luis@hermes.test",
            "active": True,
            "service_area": "Torremolinos",
            "skills": ["hormigas", "termitas"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- CUSTOMERS ---
    cust_pepe_id = "cust-pepe"
    cust_roma_id = "cust-roma"
    cust_costa_id = "cust-costa"

    service._collections["customers"] = {
        cust_pepe_id: {
            "id": cust_pepe_id,
            "name": "Bar Pepe",
            "email": "pepe@barpepe.test",
            "phone": "+34952001122",
            "telegram_user_id": "12345678",
            "whatsapp_phone": "+34600112233",
            "customer_type": "HOSPITALITY",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        cust_roma_id: {
            "id": cust_roma_id,
            "name": "Pizzería Roma",
            "email": "roma@pizzeriaroma.test",
            "phone": "+34952003344",
            "telegram_user_id": None,
            "whatsapp_phone": "+34600334455",
            "customer_type": "FOOD_BUSINESS",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        cust_costa_id: {
            "id": cust_costa_id,
            "name": "Hotel Costa",
            "email": "contacto@hotelcosta.test",
            "phone": "+34952005566",
            "telegram_user_id": None,
            "whatsapp_phone": None,
            "customer_type": "HOSPITALITY",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- SITES ---
    site_pepe_id = "site-pepe-torremolinos"
    site_roma_mlg_id = "site-roma-malaga"
    site_roma_fng_id = "site-roma-fuengirola"
    site_costa_ben_id = "site-costa-benalmadena"
    site_costa_mar_id = "site-costa-marbella"

    service._collections["sites"] = {
        site_pepe_id: {
            "id": site_pepe_id,
            "customer_id": cust_pepe_id,
            "name": "Bar Pepe Torremolinos",
            "address": "Calle San Miguel 14, Torremolinos",
            "latitude": 36.6226,
            "longitude": -4.4996,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        site_roma_mlg_id: {
            "id": site_roma_mlg_id,
            "customer_id": cust_roma_id,
            "name": "Pizzería Roma Málaga",
            "address": "Calle Larios 5, Málaga",
            "latitude": 36.7212,
            "longitude": -4.4214,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        site_roma_fng_id: {
            "id": site_roma_fng_id,
            "customer_id": cust_roma_id,
            "name": "Pizzería Roma Fuengirola",
            "address": "Paseo Marítimo 52, Fuengirola",
            "latitude": 36.5398,
            "longitude": -4.6247,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        site_costa_ben_id: {
            "id": site_costa_ben_id,
            "customer_id": cust_costa_id,
            "name": "Hotel Costa Benalmádena",
            "address": "Avenida del Sol 120, Benalmádena",
            "latitude": 36.5956,
            "longitude": -4.5249,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        site_costa_mar_id: {
            "id": site_costa_mar_id,
            "customer_id": cust_costa_id,
            "name": "Hotel Costa Marbella",
            "address": "Avenida Ricardo Soriano 24, Marbella",
            "latitude": 36.5101,
            "longitude": -4.8824,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- CONTRACTS ---
    service._collections["contracts"] = {
        "contract-pepe-cucarachas": {
            "id": "contract-pepe-cucarachas",
            "customer_id": cust_pepe_id,
            "title": "Mantenimiento Preventivo Mensual Cucarachas",
            "pest_type": "cucarachas",
            "frequency": "monthly",
            "amount": 120.0,
            "status": "active",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "next_visit_due": (datetime.now() + timedelta(days=8)).date().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "contract-costa-roedores": {
            "id": "contract-costa-roedores",
            "customer_id": cust_costa_id,
            "title": "Mantenimiento Roedores Trimestral",
            "pest_type": "roedores",
            "frequency": "quarterly",
            "amount": 350.0,
            "status": "active",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "next_visit_due": (datetime.now() + timedelta(days=22)).date().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "contract-roma-cucarachas": {
            "id": "contract-roma-cucarachas",
            "customer_id": cust_roma_id,
            "title": "Control Integrado Cucarachas y Hormigas",
            "pest_type": "cucarachas",
            "frequency": "monthly",
            "amount": 150.0,
            "status": "active",
            "start_date": "2026-03-01",
            "end_date": "2027-02-28",
            "next_visit_due": (datetime.now() + timedelta(days=12)).date().isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- INCIDENTS ---
    inc_pepe_id = "inc-pepe"
    inc_roma_id = "inc-roma"
    inc_costa_id = "inc-costa"

    service._collections["incidents"] = {
        inc_pepe_id: {
            "id": inc_pepe_id,
            "customer_id": cust_pepe_id,
            "site_id": site_pepe_id,
            "conversation_id": f"telegram:{cust_pepe_id}",
            "channel": "telegram",
            "pest_type": "cucarachas",
            "location": "Torremolinos",
            "affected_area": "Cocina y barra",
            "priority": "high",
            "operational_priority": "HIGH",
            "status": "scheduled",
            "summary": "Presencia continuada de cucarachas alemanas en zona de motores de neveras.",
            "confidence": "95%",
            "severity": "HIGH",
            "response_hours": 48,
            "assessment_reason": "Vector de plagas activo en local de hostelería.",
            "visit_type": "TREATMENT",
            "technician_level": "STANDARD",
            "dispatch_bucket": "THIS_WEEK",
            "sla_hours": 72,
            "sla_status": "ON_TRACK",
            "elapsed_hours": 12,
            "remaining_hours": 60,
            "breach_hours": None,
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        inc_roma_id: {
            "id": inc_roma_id,
            "customer_id": cust_roma_id,
            "site_id": site_roma_mlg_id,
            "conversation_id": f"whatsapp:{cust_roma_id}",
            "channel": "whatsapp",
            "pest_type": "roedores",
            "location": "Málaga",
            "affected_area": "Almacén de harinas",
            "priority": "urgent",
            "operational_priority": "URGENT",
            "status": "pending_review",
            "summary": "Avistamiento de roedores (ratas) merodeando palets de harina.",
            "confidence": "98%",
            "severity": "CRITICAL",
            "response_hours": 24,
            "assessment_reason": "Presencia de roedores en manipulación de alimentos.",
            "visit_type": "URGENT_TREATMENT",
            "technician_level": "SENIOR",
            "dispatch_bucket": "URGENT_24H",
            "sla_hours": 24,
            "sla_status": "AT_RISK",
            "elapsed_hours": 18,
            "remaining_hours": 6,
            "breach_hours": None,
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=18)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        inc_costa_id: {
            "id": inc_costa_id,
            "customer_id": cust_costa_id,
            "site_id": site_costa_ben_id,
            "conversation_id": f"email:{cust_costa_id}",
            "channel": "email",
            "pest_type": "cucarachas",
            "location": "Benalmádena",
            "affected_area": "Terrazas exteriores",
            "priority": "medium",
            "operational_priority": "NORMAL",
            "status": "completed",
            "summary": "Control preventivo de insectos rastreros en zonas comunes del jardín.",
            "confidence": "90%",
            "severity": "LOW",
            "response_hours": 72,
            "assessment_reason": "Control rutinario preventivo exterior.",
            "visit_type": "INSPECTION",
            "technician_level": "JUNIOR",
            "dispatch_bucket": "PLANNED",
            "sla_hours": 96,
            "sla_status": "COMPLETED",
            "elapsed_hours": 48,
            "remaining_hours": 0,
            "breach_hours": None,
            "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- VISITS ---
    visit_pepe_id = "visit-pepe"
    visit_roma_id = "visit-roma"
    visit_costa_id = "visit-costa"

    service._collections["visits"] = {
        visit_pepe_id: {
            "id": visit_pepe_id,
            "incident_id": inc_pepe_id,
            "technician_id": tech_pedro_id,
            "scheduled_start": (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0).isoformat(),
            "scheduled_end": (datetime.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0).isoformat(),
            "status": "scheduled",
            "address": "Calle San Miguel 14, Torremolinos",
            "notes": "Desinsectación preventiva integral de la cocina con gel químico.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        visit_roma_id: {
            "id": visit_roma_id,
            "incident_id": inc_roma_id,
            "technician_id": tech_ana_id,
            "scheduled_start": (datetime.now() + timedelta(hours=2)).replace(minute=0, second=0).isoformat(),
            "scheduled_end": (datetime.now() + timedelta(hours=4)).replace(minute=0, second=0).isoformat(),
            "status": "in_progress",
            "address": "Calle Larios 5, Málaga",
            "notes": "Revisión urgente de trampas cebaderas e inspección de sellado de bajantes.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        visit_costa_id: {
            "id": visit_costa_id,
            "incident_id": inc_costa_id,
            "technician_id": tech_luis_id,
            "scheduled_start": (datetime.now() - timedelta(days=1)).replace(hour=10, minute=0, second=0).isoformat(),
            "scheduled_end": (datetime.now() - timedelta(days=1)).replace(hour=12, minute=0, second=0).isoformat(),
            "status": "completed",
            "address": "Avenida del Sol 120, Benalmádena",
            "notes": "Fumigación de setos y sumideros del jardín perimetral. Cebo líquido colocado.",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- CONVERSATIONS ---
    conv_pepe_id = f"telegram:{cust_pepe_id}"
    conv_roma_id = f"whatsapp:{cust_roma_id}"
    conv_costa_id = f"email:{cust_costa_id}"

    service._collections["conversations"] = {
        conv_pepe_id: {
            "id": conv_pepe_id,
            "channel": "telegram",
            "external_user_id": cust_pepe_id,
            "external_chat_id": cust_pepe_id,
            "status": "active",
            "customer_id": cust_pepe_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        conv_roma_id: {
            "id": conv_roma_id,
            "channel": "whatsapp",
            "external_user_id": cust_roma_id,
            "external_chat_id": cust_roma_id,
            "status": "active",
            "customer_id": cust_roma_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        conv_costa_id: {
            "id": conv_costa_id,
            "channel": "email",
            "external_user_id": cust_costa_id,
            "external_chat_id": cust_costa_id,
            "status": "active",
            "customer_id": cust_costa_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- MESSAGES ---
    service._collections["messages"] = {
        "msg-1": {
            "id": "msg-1",
            "conversation_id": conv_pepe_id,
            "direction": "inbound",
            "channel": "telegram",
            "text": "Hola, soy Pepe de Bar Pepe en Torremolinos. Tenemos un problema grave con cucarachas en la cocina y la barra. ¿Pueden mandar un técnico pronto?",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=12, minutes=5)).isoformat(),
        },
        "msg-2": {
            "id": "msg-2",
            "conversation_id": conv_pepe_id,
            "direction": "outbound",
            "channel": "telegram",
            "text": "Hola Pepe, he registrado tu solicitud. Evaluando severidad del vector de plagas...",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=12, minutes=4)).isoformat(),
        },
        "msg-3": {
            "id": "msg-3",
            "conversation_id": conv_pepe_id,
            "direction": "outbound",
            "channel": "telegram",
            "text": "Incidencia registrada con éxito. Un supervisor ha programado tu visita para mañana a las 9:00 AM con nuestro técnico Pedro.",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        },
        "msg-4": {
            "id": "msg-4",
            "conversation_id": conv_roma_id,
            "direction": "inbound",
            "channel": "whatsapp",
            "text": "Buenas, del Almacén de Harinas de Pizzería Roma. Se han visto dos ratas grandes cerca de los sacos. Esto es urgente por Sanidad.",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=18, minutes=10)).isoformat(),
        },
        "msg-5": {
            "id": "msg-5",
            "conversation_id": conv_roma_id,
            "direction": "outbound",
            "channel": "whatsapp",
            "text": "Hola, hemos recibido tu reporte. Clasificando caso como crítico y enviándolo al supervisor para su inmediata asignación de técnico.",
            "created_at": (datetime.now(timezone.utc) - timedelta(hours=18, minutes=8)).isoformat(),
        },
    }

    # --- OPERATIONAL DOCUMENTS ---
    doc_pepe_id = "doc-pepe"
    doc_roma_id = "doc-roma"
    doc_costa_id = "doc-costa"

    service._collections["operational_documents"] = {
        doc_pepe_id: {
            "id": doc_pepe_id,
            "document_type": "technician_brief",
            "incident_id": inc_pepe_id,
            "visit_id": visit_pepe_id,
            "title": f"Brief técnico visita {visit_pepe_id}",
            "content": "Brief operativo para técnico Pedro:\nLocalidad: Torremolinos\nPlaga: Cucarachas\nNotas: Desinsectación preventiva en cocina y barra.",
            "status": "draft",
            "generated_by": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        doc_roma_id: {
            "id": doc_roma_id,
            "document_type": "incident_summary",
            "incident_id": inc_roma_id,
            "title": f"Resumen de incidencia {inc_roma_id}",
            "content": "Resumen de emergencia para Pizzería Roma:\nPlaga: Roedores\nLocalidad: Málaga\nNotas: Presencia crítica en almacén.",
            "status": "reviewed",
            "generated_by": "system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # --- OPERATIONAL DOCUMENT VERSIONS ---
    service._collections["operational_document_versions"] = {
        "ver-pepe-1": {
            "id": "ver-pepe-1",
            "document_id": doc_pepe_id,
            "version_number": 1,
            "content": "Brief operativo para técnico Pedro:\nLocalidad: Torremolinos\nPlaga: Cucarachas\nNotas: Desinsectación preventiva en cocina y barra.",
            "generated_by": "system",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        "ver-roma-1": {
            "id": "ver-roma-1",
            "document_id": doc_roma_id,
            "version_number": 1,
            "content": "Resumen de emergencia para Pizzería Roma:\nPlaga: Roedores\nLocalidad: Málaga\nNotas: Presencia crítica en almacén.",
            "generated_by": "system",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    print("Seeding complete.")
