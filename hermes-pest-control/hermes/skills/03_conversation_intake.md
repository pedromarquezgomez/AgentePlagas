# 03 Conversation Intake

Conversation intake converts a normalized message into an operational decision.

Current sprint behavior:

1. Receive `IncomingMessage`.
2. Build `conversation_id` as `channel:external_user_id`.
3. Send message to `HermesService`.
4. If Hermes returns `create_incident`, call `IncidentService`.
5. Return `AgentResponse`.

Future behavior:

- Load existing conversation state from Firestore.
- Store message history.
- Track missing fields.
- Resume intake across multiple messages.

