import pytest
from app.pests.classifier import PestClassifier


def test_classify_cockroach() -> None:
    classifier = PestClassifier()
    result = classifier.classify("Tengo cucarachas en la cocina")
    assert result.pest_type == "COCKROACH"
    assert result.confidence == "high"
    assert result.recommended_priority == "high"
    assert result.requires_human_review is False
    assert "cucarachas" in result.detected_terms
    assert result.evidence == "cucarachas"
    assert result.pest_type_spanish == "cucarachas"


def test_classify_rodent() -> None:
    classifier = PestClassifier()
    result = classifier.classify("He visto unas ratas en el sótano")
    assert result.pest_type == "RODENT"
    assert result.confidence == "high"
    assert result.recommended_priority == "high"
    assert result.requires_human_review is False
    assert "ratas" in result.detected_terms
    assert result.evidence == "ratas"
    assert result.pest_type_spanish == "roedores"


def test_classify_ant() -> None:
    classifier = PestClassifier()
    result = classifier.classify("Hay hormigas en el jardín")
    assert result.pest_type == "ANT"
    assert result.confidence == "high"
    assert result.recommended_priority == "medium"
    assert result.requires_human_review is False
    assert "hormigas" in result.detected_terms
    assert result.evidence == "hormigas"
    assert result.pest_type_spanish == "hormigas"


def test_classify_flying_insect() -> None:
    classifier = PestClassifier()
    result = classifier.classify("Hay mosquitos y avispas volando cerca")
    assert result.pest_type == "FLYING_INSECT"
    assert result.confidence == "high"
    assert result.recommended_priority == "medium"
    assert result.requires_human_review is False
    # detected_terms ordena por longitud descendente de la taxonomía, así que 'mosquitos' y 'avispas' coincidirán
    assert "mosquitos" in result.detected_terms
    assert "avispas" in result.detected_terms
    assert result.evidence in {"mosquitos", "avispas"}  # Depende de cuál detectó como primary
    assert result.pest_type_spanish == "mosquitos/avispas"


def test_classify_stored_product_insect() -> None:
    classifier = PestClassifier()
    result = classifier.classify("Hay gorgojo en la harina y polillas en la despensa")
    assert result.pest_type == "STORED_PRODUCT_INSECT"
    assert result.confidence == "high"
    assert result.recommended_priority == "medium"
    assert result.requires_human_review is False
    assert "gorgojo" in result.detected_terms
    assert "polillas" in result.detected_terms
    assert result.evidence in {"gorgojo", "polillas"}
    assert result.pest_type_spanish == "gorgojo/polilla"


def test_classify_unknown_sensible() -> None:
    classifier = PestClassifier()
    result = classifier.classify("Hay unos bichos raros que no reconozco")
    assert result.pest_type == "UNKNOWN"
    assert result.confidence == "high"
    assert result.requires_human_review is True
    assert "bichos raros" in result.detected_terms
    assert result.evidence == "bichos raros"
    assert result.pest_type_spanish is None


def test_classify_no_match() -> None:
    classifier = PestClassifier()
    result = classifier.classify("Hola, buenos días, quería hacer una consulta")
    assert result.pest_type is None
    assert result.confidence is None
    assert result.evidence is None
    assert result.detected_terms == []
    assert result.requires_human_review is False
