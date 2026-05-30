# 05 Agent Response Contract

`AgentResponse` is the contract returned by Hermes-facing logic.

Fields:

- `reply`: text to send back to the user.
- `action`: machine-readable backend instruction.
- `incident`: incident proposal or context.

Known action types:

- `create_incident`
- `collect_missing_data`
- `escalate_to_human`

Hermes responses should be deterministic enough for backend services to execute safely.
