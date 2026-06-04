from app.context.customer_context_builder import CustomerContext

class RecurrenceService:
    """
    Evalúa si la incidencia actual es una reincidencia basada en el contexto del cliente.
    """
    
    def __init__(self, time_window_days: int = 180):
        self.time_window_days = time_window_days

    def detect_recurrence(
        self, 
        current_pest_type: str | None, 
        customer_context: CustomerContext
    ) -> bool:
        if not customer_context.last_incident_date or customer_context.days_since_last_incident is None:
            return False
            
        if customer_context.days_since_last_incident > self.time_window_days:
            return False
            
        # Si no sabemos la plaga actual, podríamos asumirla de la anterior en el flujo real,
        # pero si sabemos ambas, comprobamos que coincidan.
        # Si current_pest_type es None, dejamos que el flujo lo decida más adelante,
        # pero al menos marcamos como potencial reincidencia si hay historial reciente.
        if current_pest_type and customer_context.last_pest_type:
            # En un entorno real podríamos mapear "cucarachas" a "COCKROACH", etc.
            # Aquí asumimos que están normalizados.
            if current_pest_type.casefold() == customer_context.last_pest_type.casefold():
                return True
        elif not current_pest_type and customer_context.last_pest_type:
            # Si no ha especificado plaga pero el intent classifier dijo "han vuelto", 
            # asumimos que es de la misma plaga.
            return True
            
        return False
