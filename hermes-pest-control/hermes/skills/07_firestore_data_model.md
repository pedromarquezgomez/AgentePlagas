# 07 Firestore Data Model

Firestore is the future source of truth.

Suggested collections:

- `clients`
- `conversations`
- `messages`
- `incidents`
- `escalations`

Suggested document IDs:

- Conversations: `channel:external_user_id`
- Incidents: generated UUID or Firestore auto ID
- Clients: generated UUID or canonical CRM ID

Firestore integration should stay behind `FirestoreService`.

