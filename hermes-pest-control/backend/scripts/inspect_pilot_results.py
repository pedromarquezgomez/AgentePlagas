import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config.settings import Settings
from app.services.firestore_factory import get_firestore_service


async def main():
    settings = Settings()
    # Usar Firestore real configurado en el entorno
    service = get_firestore_service(settings)

    print("--- ÚLTIMOS 5 DECISION RECORDS ---")
    records = await service.list_documents("decision_records", limit=5)
    # Ordenar por id o fecha si está disponible
    records_sorted = sorted(
        records,
        key=lambda x: x.get("created_at") or x.get("id") or "",
        reverse=True,
    )
    for r in records_sorted:
        print(f"ID: {r.get('id')}")
        print(f"  Conversation ID: {r.get('conversation_id')}")
        print(f"  Channel: {r.get('channel')}")
        print(f"  Pilot Mode Enabled: {r.get('pilot_mode_enabled')}")
        print(f"  Pilot Used: {r.get('pilot_used')}")
        print(f"  Pilot Blocked: {r.get('pilot_blocked')}")
        print(f"  Pilot Route: {r.get('pilot_route')}")
        print(f"  Pilot Policy Rule: {r.get('pilot_policy_rule')}")
        print(f"  Risk Flags: {r.get('pilot_risk_flags')}")
        print(f"  Action Type: {r.get('action_type')}")
        print(f"  Pest Type: {r.get('pest_type')}")
        print(f"  Priority: {r.get('priority')}")
        print("-" * 30)

    print("\n--- ÚLTIMOS 5 HUMAN REVIEW ITEMS ---")
    reviews = await service.list_documents("human_review_items", limit=5)
    reviews_sorted = sorted(
        reviews,
        key=lambda x: x.get("created_at") or x.get("id") or "",
        reverse=True,
    )
    for h in reviews_sorted:
        print(f"ID: {h.get('id')}")
        print(f"  Conversation ID: {h.get('conversation_id')}")
        print(f"  Reason: {h.get('reason')}")
        print(f"  Priority: {h.get('priority')}")
        print(f"  Summary: {h.get('summary')}")
        print("-" * 30)


if __name__ == "__main__":
    asyncio.run(main())
