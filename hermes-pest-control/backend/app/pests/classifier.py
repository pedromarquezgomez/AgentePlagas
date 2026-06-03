import re
from app.pests.contracts import PestClassification
from app.pests.taxonomy import PEST_TERM_TO_TYPE, PEST_TYPE_METADATA


class PestClassifier:
    def __init__(self) -> None:
        self.term_to_type = PEST_TERM_TO_TYPE
        self.metadata = PEST_TYPE_METADATA

    def classify(self, text: str) -> PestClassification:
        if not text:
            return PestClassification()

        text_lower = text.casefold()
        detected_terms = []
        primary_term = None

        # Ordenar términos por longitud descendente para evitar falsos positivos parciales (ej. "bichos raros" antes que "bichos")
        sorted_terms = sorted(self.term_to_type.keys(), key=len, reverse=True)

        for term in sorted_terms:
            matched = False
            if len(term) <= 4:
                pattern = rf"\b{re.escape(term)}\b"
                if re.search(pattern, text_lower):
                    matched = True
            else:
                if term in text_lower:
                    matched = True

            if matched:
                detected_terms.append(term)
                if primary_term is None:
                    primary_term = term

        if not primary_term:
            return PestClassification()

        # Obtener tipo de plaga y sus metadatos de negocio
        pest_type = self.term_to_type[primary_term]
        meta = self.metadata[pest_type]

        # Extraer la evidencia exacta respetando mayúsculas/minúsculas del texto original
        evidence = primary_term
        match = re.search(re.escape(primary_term), text_lower)
        if match:
            start, end = match.span()
            evidence = text[start:end]

        return PestClassification(
            pest_type=pest_type,
            confidence="high",
            evidence=evidence,
            detected_terms=detected_terms,
            recommended_priority=meta["priority"],
            requires_human_review=meta["requires_human_review"],
            pest_type_spanish=meta["spanish"],
        )

