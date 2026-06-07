import re

class SecurityPolicy:
    SENSITIVE_TERMS = [
        "intoxic", "he respirado", "mareo", "urgencias", "mascota", "perro", "gato",
        "denuncia", "reclamación", "reclamacion", "muy enfadado", "producto químico",
        "producto quimico", "mezclar", "lejía", "lejia", "amoniaco", "garantía total",
        "garantia total", "precio cerrado"
    ]

    @classmethod
    def requires_human_review(cls, text: str) -> bool:
        if not text:
            return False
        cleaned_text = text.lower().replace("bar pepe", "").replace("mi bar", "")
        return any(term in cleaned_text for term in cls.SENSITIVE_TERMS)

    @classmethod
    def is_sensitive(cls, text: str) -> bool:
        return cls.requires_human_review(text)

    @classmethod
    def get_sensitive_terms(cls) -> list[str]:
        return cls.SENSITIVE_TERMS
