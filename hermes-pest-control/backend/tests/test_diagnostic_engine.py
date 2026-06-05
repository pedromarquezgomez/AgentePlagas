import pytest
from app.diagnostics.diagnostic_engine import DiagnosticEngine
from app.diagnostics.contracts import DiagnosisState

@pytest.mark.asyncio
async def test_diagnostic_engine_plant_pest() -> None:
    engine = DiagnosticEngine()
    assessment = await engine.assess("Tengo unos bichos verdes en un limonero")
    assert assessment.state == DiagnosisState.DIAGNOSIS
    assert assessment.knowledge_key == "plant_pests"
    assert len(assessment.hypotheses) > 0
    assert assessment.hypotheses[0].label == "pulgón verde"

@pytest.mark.asyncio
async def test_diagnostic_engine_out_of_domain() -> None:
    engine = DiagnosticEngine()
    assessment = await engine.assess("Me lavo los pies")
    assert assessment.state == DiagnosisState.OUT_OF_DOMAIN

@pytest.mark.asyncio
async def test_diagnostic_engine_intake_known_pest() -> None:
    engine = DiagnosticEngine()
    assessment = await engine.assess("Tengo cucarachas en la cocina")
    assert assessment.state == DiagnosisState.DISCOVERY
