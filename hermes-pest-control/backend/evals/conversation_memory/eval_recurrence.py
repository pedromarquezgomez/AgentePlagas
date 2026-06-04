import asyncio
from datetime import datetime, timezone, timedelta
from app.conversation.intent_classifier import IntentClassifier, IntentType
from app.context.customer_context_builder import CustomerContext, CustomerContextBuilder
from app.incidents.recurrence_service import RecurrenceService

async def main():
    print("Testing Intent Classifier...")
    classifier = IntentClassifier()
    assert classifier.classify("Me han vuelto a salir cucarachas") == IntentType.RECURRENCE
    assert classifier.classify("Hola, ¿cómo va mi incidencia?") == IntentType.STATUS_CHECK
    assert classifier.classify("Tengo hormigas en la cocina") == IntentType.NEW_INCIDENT
    print("Intent Classifier OK.")

    print("Testing Recurrence Service...")
    svc = RecurrenceService(time_window_days=180)
    
    # Context 1: Last incident 30 days ago, same pest
    ctx1 = CustomerContext(
        customer_id="cust-123",
        last_incident_id="inc-1",
        last_pest_type="COCKROACH",
        last_incident_date=(datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        days_since_last_incident=30
    )
    assert svc.detect_recurrence("COCKROACH", ctx1) == True
    
    # Context 2: Different pest
    assert svc.detect_recurrence("RODENT", ctx1) == False
    
    # Context 3: Out of time window
    ctx2 = CustomerContext(
        customer_id="cust-123",
        last_incident_id="inc-1",
        last_pest_type="COCKROACH",
        last_incident_date=(datetime.now(timezone.utc) - timedelta(days=200)).isoformat(),
        days_since_last_incident=200
    )
    assert svc.detect_recurrence("COCKROACH", ctx2) == False
    print("Recurrence Service OK.")

if __name__ == "__main__":
    asyncio.run(main())
