import re
import unicodedata

from app.schemas.incoming_message import IncomingMessage
from app.schemas.pilot_gate import PilotGateResult


class HermesPilotGate:
    pest_terms = [
        "cucaracha",
        "cucarachas",
        "hormiga",
        "hormigas",
        "chinche",
        "chinches",
        "avispa",
        "avispas",
        "roedor",
        "roedores",
        "rata",
        "ratas",
        "raton",
        "ratones",
    ]
    area_terms = [
        "cocina",
        "jardin",
        "dormitorio",
        "terraza",
        "garaje",
        "bano",
        "salon",
        "almacen",
        "local",
    ]
    location_terms = [
        "torremolinos",
        "malaga",
        "benalmadena",
        "fuengirola",
        "marbella",
        "mijas",
    ]

    def evaluate(self, message: IncomingMessage) -> PilotGateResult:
        text = self._normalize(message.text or "")
        if self._is_ambiguous(text):
            return self._mock(
                "El mensaje no contiene datos suficientes para delegar en el agente.",
                ["ambiguous_message"],
                "pilot.ambiguous_message",
            )

        safety_flags = self._safety_flags(text)
        if safety_flags:
            return PilotGateResult(
                eligible=False,
                reason="Caso sensible: requiere revisión humana antes de delegar.",
                risk_flags=safety_flags,
                route="human_review",
                policy_rule="pilot.sensitive_case",
            )

        if self._asks_for_exact_price(text):
            return self._mock(
                "El cliente pide precio cerrado o exacto; se mantiene el flujo actual.",
                ["price_request"],
                "pilot.price_request",
            )

        if self._has_clear_intake(text):
            return PilotGateResult(
                eligible=True,
                reason="Caso simple con plaga, zona afectada y localidad.",
                risk_flags=[],
                route="agent",
                policy_rule="pilot.simple_intake",
            )

        return self._mock(
            "Faltan datos operativos o hay duda razonable.",
            ["incomplete_intake"],
            "pilot.incomplete_intake",
        )

    def _safety_flags(self, text: str) -> list[str]:
        checks = [
            ("chemical_request", self._contains(text, [
                "producto quimico",
                "insecticida",
                "veneno",
                "fumigar",
                "fumigue",
                "mezclar",
                "lejia",
                "amoniaco",
                "dosis",
            ])),
            ("exposure_or_pet", self._contains(text, [
                "mascota",
                "perro",
                "gato",
                "toco producto",
                "ha tocado",
                "lamio",
                "intoxic",
                "mareo",
                "he respirado",
            ])),
            ("vulnerable_person", self._contains(text, [
                "bebe",
                "nino",
                "nina",
                "menor",
                "anciano",
                "mayor",
                "embarazada",
                "vulnerable",
                "enfermo",
            ])),
            ("food_business", self._contains(text, [
                "restaurante",
                "bar",
                "cocina profesional",
                "negocio alimentario",
                "industria alimentaria",
                "cafeteria",
                "carniceria",
                "panaderia",
            ])),
            ("angry_or_legal", self._contains(text, [
                "denuncia",
                "abogado",
                "reclamacion",
                "muy enfadado",
                "furioso",
                "estafa",
                "voy a denunciar",
                "amenaza",
            ])),
            ("dangerous_instructions", self._contains(text, [
                "como mezclo",
                "como mezclar",
                "que producto uso",
                "recomiendame un producto",
                "dime un quimico",
            ])),
        ]
        flags = [flag for flag, present in checks if present]

        if self._contains(text, ["roedor", "roedores", "rata", "ratas", "raton", "ratones"]) and (
            self._contains(text, ["denuncia", "enfadado", "furioso", "restaurante", "bar"])
        ):
            flags.append("rodent_conflict")

        return sorted(set(flags))

    def _has_clear_intake(self, text: str) -> bool:
        return (
            self._contains(text, self.pest_terms)
            and self._contains(text, self.area_terms)
            and self._contains(text, self.location_terms)
        )

    def _is_ambiguous(self, text: str) -> bool:
        if len(text.strip()) < 8:
            return True
        return not self._contains(text, self.pest_terms) and len(text.split()) < 6

    def _asks_for_exact_price(self, text: str) -> bool:
        return self._contains(text, [
            "precio exacto",
            "precio cerrado",
            "cuanto cuesta",
            "presupuesto cerrado",
            "tarifa fija",
            "dime el precio",
        ])

    def _mock(
        self,
        reason: str,
        risk_flags: list[str],
        policy_rule: str,
    ) -> PilotGateResult:
        return PilotGateResult(
            eligible=False,
            reason=reason,
            risk_flags=risk_flags,
            route="mock",
            policy_rule=policy_rule,
        )

    def _contains(self, text: str, terms: list[str]) -> bool:
        return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)

    def _normalize(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.casefold())
        without_marks = "".join(
            char for char in normalized if not unicodedata.combining(char)
        )
        return re.sub(r"\s+", " ", without_marks).strip()


PilotGateService = HermesPilotGate

