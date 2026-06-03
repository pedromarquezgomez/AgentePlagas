import re
from app.pests.contracts import ClassifiedPest
from app.pests.taxonomy import PEST_TAXONOMY_TERMS


class PestClassifier:
    def __init__(self) -> None:
        self.terms = PEST_TAXONOMY_TERMS

    def classify(self, text: str) -> ClassifiedPest:
        if not text:
            return ClassifiedPest()

        text_lower = text.casefold()
        for term, spanish_term in self.terms.items():
            if len(term) <= 4:
                pattern = rf"\b{re.escape(term)}\b"
                if re.search(pattern, text_lower):
                    return self._build_classified_pest(spanish_term)
            else:
                if term in text_lower:
                    return self._build_classified_pest(spanish_term)

        return ClassifiedPest()

    def _build_classified_pest(self, spanish_term: str) -> ClassifiedPest:
        if spanish_term == "cucarachas":
            return ClassifiedPest(pest_type="cockroach", pest_type_spanish="cucarachas")
        elif spanish_term == "roedores":
            return ClassifiedPest(pest_type="rodent", pest_type_spanish="roedores")
        elif spanish_term == "hormigas":
            return ClassifiedPest(pest_type="ant", pest_type_spanish="hormigas")
        elif spanish_term == "unknown":
            return ClassifiedPest(pest_type="unknown", pest_type_spanish=None)
        else:
            return ClassifiedPest(pest_type="unknown", pest_type_spanish=None)
