# 00 Project Architecture

Hermes Pest Control System is organized around channel-agnostic business services.

Main layers:

- `adapters`: translate provider payloads into normalized messages.
- `schemas`: define internal contracts with Pydantic.
- `services`: contain orchestration and business workflows.
- `routes`: expose HTTP entry points.
- `prompts`: hold agent instructions.
- `config`: centralize environment settings.

Rules:

- Adapters must not create incidents, classify priorities, or mutate business records.
- `ConversationService` is the entry point for normalized message handling.
- `HermesService` is an abstraction and may be mock, HTTP, SDK, or local agent backed.
- `FirestoreService` owns persistence integration.

