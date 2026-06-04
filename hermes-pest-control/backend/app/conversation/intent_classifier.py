from enum import Enum
import re

class IntentType(str, Enum):
    NEW_INCIDENT = "NEW_INCIDENT"
    RECURRENCE = "RECURRENCE"
    STATUS_CHECK = "STATUS_CHECK"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"

class IntentClassifier:
    """
    Clasifica la intención del primer mensaje de un cliente para enrutar
    rápidamente sin necesidad de invocar al LLM completo.
    """

    def __init__(self):
        self.recurrence_keywords = [
            "vuelto a salir", "otra vez", "de nuevo", "sigue habiendo", "siguen", 
            "todavía hay", "reaparecido", "no ha funcionado", "sigo viendo",
            "vuelven a", "vuelve a", "reincidencia"
        ]
        
        self.status_keywords = [
            "estado", "cómo va", "como va", "cuando vienen", "cuándo vienen",
            "qué ha pasado con", "que ha pasado con", "para cuando", "para cuándo",
            "información de mi", "informacion de mi"
        ]

    def classify(self, text: str) -> IntentType:
        if not text:
            return IntentType.NEW_INCIDENT
            
        text_lower = text.casefold()

        # 1. Comprobar status check (ej. "¿cómo va mi incidencia?")
        for kw in self.status_keywords:
            if kw in text_lower:
                # Filtrar si es un mensaje mixto, pero por defecto a status check
                return IntentType.STATUS_CHECK

        # 2. Comprobar reincidencia (ej. "Me han vuelto a salir cucarachas")
        for kw in self.recurrence_keywords:
            if kw in text_lower:
                return IntentType.RECURRENCE

        # Por defecto asumimos que es una nueva incidencia (o inquiry general que el LLM manejará)
        return IntentType.NEW_INCIDENT
