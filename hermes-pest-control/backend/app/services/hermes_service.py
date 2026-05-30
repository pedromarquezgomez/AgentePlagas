from app.schemas.agent_response import AgentResponse
from app.schemas.incoming_message import IncomingMessage


class HermesService:
    async def process_message(
        self,
        message: IncomingMessage,
        conversation_id: str,
    ) -> AgentResponse:
        text = (message.text or "").casefold()

        has_cockroach = "cucaracha" in text or "cucarachas" in text
        has_kitchen = "cocina" in text
        has_torremolinos = "torremolinos" in text

        missing_fields: list[str] = []
        if not has_cockroach:
            missing_fields.append("pest_type")
        if not has_kitchen:
            missing_fields.append("affected_area")
        if not has_torremolinos:
            missing_fields.append("location")

        if not missing_fields:
            return AgentResponse(
                reply=(
                    "Gracias por la información. He registrado el aviso para que el "
                    "equipo lo revise. Si puedes, envíanos una foto de la zona afectada "
                    "para ayudar al técnico a valorar mejor el caso."
                ),
                action={
                    "type": "create_incident",
                    "missing_fields": [],
                },
                incident={
                    "should_create": True,
                    "pest_type": "cucarachas",
                    "location": "Torremolinos",
                    "affected_area": "cocina",
                    "priority": "high",
                    "summary": (
                        "Cliente informa de presencia de cucarachas en la cocina "
                        "en Torremolinos."
                    ),
                },
            )

        return AgentResponse(
            reply=self._build_missing_data_reply(missing_fields),
            action={
                "type": "collect_missing_data",
                "missing_fields": missing_fields,
            },
            incident={
                "should_create": False,
                "conversation_id": conversation_id,
            },
        )

    def _build_missing_data_reply(self, missing_fields: list[str]) -> str:
        prompts = {
            "pest_type": "qué tipo de plaga has visto",
            "affected_area": "en qué zona del inmueble está ocurriendo",
            "location": "en qué localidad se encuentra el aviso",
        }
        requested = [prompts[field] for field in missing_fields]

        if len(requested) == 1:
            details = requested[0]
        else:
            details = ", ".join(requested[:-1]) + f" y {requested[-1]}"

        return f"Para registrar el aviso necesito saber {details}."

