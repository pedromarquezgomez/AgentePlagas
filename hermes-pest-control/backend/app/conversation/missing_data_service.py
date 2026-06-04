from app.context.customer_context_builder import CustomerContext

class MissingDataService:
    """
    Evalúa qué campos faltan teniendo en cuenta tanto lo que el usuario ha dicho
    en el mensaje actual como lo que ya sabemos de su CustomerContext histórico.
    """
    
    @staticmethod
    def resolve_missing_fields(
        detected_missing_fields: list[str], 
        customer_context: CustomerContext
    ) -> list[str]:
        resolved_missing = list(detected_missing_fields)
        
        # Si ya conocemos al cliente por su historial, no le pedimos el nombre
        if "customer_name" in resolved_missing and customer_context.customer_name:
            resolved_missing.remove("customer_name")
            
        # Podríamos omitir la ubicación si es un cliente recurrente, ya la sabemos y NO tiene múltiples locales
        if "location" in resolved_missing and customer_context.last_location and not customer_context.has_multiple_sites:
            resolved_missing.remove("location")
            
        return resolved_missing
