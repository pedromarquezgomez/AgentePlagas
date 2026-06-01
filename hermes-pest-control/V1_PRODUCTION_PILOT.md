# V1 Production Pilot

Hermes Pest Control System V1 is deployed as a production pilot for operational
validation with real Firebase Hosting, Cloud Run, Firebase Auth, Firestore, and
Telegram intake.

## Production URLs

- Frontend Firebase Hosting: https://control-plagas-ai.web.app
- Backend Cloud Run: https://hermes-pest-control-backend-601698914613.europe-west1.run.app
- Telegram webhook: https://hermes-pest-control-backend-601698914613.europe-west1.run.app/webhooks/telegram

## Deployed Architecture

```text
Firebase Hosting
  -> Vue 3 operations panel
  -> Cloud Run FastAPI backend
  -> Firebase Auth for operator login
  -> Firestore as source of truth

Telegram Bot API
  -> Cloud Run /webhooks/telegram
  -> TelegramAdapter
  -> ConversationService
  -> HermesService mock
  -> IncidentService / DecisionAuditService / HumanReviewService
  -> Firestore
```

The backend remains channel-agnostic. Telegram and future channels normalize
messages into `IncomingMessage`; business logic stays in services behind
`ConversationService`.

## Current System Status

- Firebase Auth login works in production.
- Frontend sends `Authorization: Bearer <Firebase ID token>` for protected API calls.
- Backend validates Firebase ID tokens.
- Firestore real is active and used by production.
- Telegram real creates incidents through the webhook.
- The panel displays incidents created from Telegram.
- Operational modules are available: dashboard, incidents, human review,
  technicians, visits, internal calendar, documents, and audit endpoints.
- CORS is configured for `https://control-plagas-ai.web.app`.
- `POST /messages/test` is unavailable in production by design.
- Hermes remains in `HERMES_MODE=mock` for the production pilot.

## Validated End-To-End Flow

```text
Telegram user message
  -> Telegram webhook on Cloud Run
  -> TelegramAdapter.parse_incoming
  -> ConversationService
  -> HermesService mock
  -> IncidentService creates pending_review incident
  -> DecisionAuditService creates DecisionRecord
  -> Firestore persists records
  -> TelegramAdapter sends bot reply
  -> Firebase Hosting panel shows incident
```

Validated example:

```text
Tengo cucarachas en la cocina en Torremolinos desde hace una semana
```

Expected outcome:

- Bot replies confirming the aviso was registered.
- Incident appears in the panel with `channel=telegram`.
- Incident fields include pest type, affected area, location, status, priority,
  and summary.

## Critical Production Variables

Do not commit real values. Configure secrets through Cloud Run environment
variables, Secret Manager, Firebase settings, or local ignored `.env` files.

Backend:

```bash
APP_ENV=production
AUTH_MODE=firebase
FIREBASE_AUTH_ENABLED=true
FIREBASE_PROJECT_ID=control-plagas-ai
CORS_ALLOWED_ORIGINS=https://control-plagas-ai.web.app
FRONTEND_PUBLIC_URL=https://control-plagas-ai.web.app
HERMES_MODE=mock
TELEGRAM_BOT_TOKEN=<secret>
TELEGRAM_WEBHOOK_SECRET=<optional-secret>
WHATSAPP_ENABLED=false
GOOGLE_CALENDAR_ENABLED=false
```

Frontend:

```bash
VITE_API_BASE_URL=https://hermes-pest-control-backend-601698914613.europe-west1.run.app
VITE_AUTH_MODE=firebase
VITE_FIREBASE_API_KEY=<public-web-config>
VITE_FIREBASE_AUTH_DOMAIN=control-plagas-ai.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=control-plagas-ai
VITE_FIREBASE_STORAGE_BUCKET=<public-web-config>
VITE_FIREBASE_MESSAGING_SENDER_ID=<public-web-config>
VITE_FIREBASE_APP_ID=<public-web-config>
```

## Production Health Checklist

- `GET /health` returns `{"status":"ok"}`.
- `GET /ready` returns `status=ready`.
- Firebase Auth is enabled.
- Firestore real is active.
- CORS allows `https://control-plagas-ai.web.app`.
- Telegram webhook points to Cloud Run.
- Frontend production bundle points to Cloud Run.
- `GET /incidents` without token returns `401`.
- `GET /incidents` with Firebase Bearer token returns `200`.
- `/config/status` exposes only booleans and safe mode names, never secrets.

## Manual Validation Checklist

- Login in frontend.
- Dashboard loads.
- Telegram creates an incident.
- Incident appears in panel.
- Open incident detail.
- Change incident status.
- Add internal note.
- Generate operational incident summary.
- Create technician.
- Create visit associated with incident.
- View visit in calendar.
- Generate document.
- Check `DecisionRecord` in Firestore.
- Check `HumanReviewItem` if escalation or fallback occurs.

## Known Risks

- V1 uses `HERMES_MODE=mock`; it is not yet a production real-agent decisioning
  system.
- Firebase Auth has basic user authentication but no advanced roles or
  multi-company authorization.
- Google Calendar is optional and not the source of truth.
- WhatsApp is adapter-ready but not validated as a real production channel.
- Operational documents are internal drafts, not official legal certificates.
- Manual workflows are intentionally simple and may need UX hardening after
  operator feedback.

## Current Limitations

- No real Hermes Agent in production.
- No WhatsApp real channel in production.
- No advanced roles.
- No multi-company SaaS model.
- No mobile app.
- No billing.
- No official legal certificate generation.
- No route optimization.
- No automatic technician assignment by Hermes.

## Next Recommended Phase

Sprint 18 should be **controlled real-agent activation**.

Before enabling any real Hermes agent path in production:

- Run real-mode evals against the Hermes Agent wrapper.
- Test real mode through `/messages/test` or an isolated backend environment.
- Review generated `DecisionRecord` entries.
- Keep safe fallback active.
- Keep Human Review active.
- Do not connect Telegram to `HERMES_MODE=real` until real-mode evals and
  manual review are acceptable.

Recommended rollout:

1. Run Hermes real against offline evals.
2. Run Hermes real against `/messages/test`.
3. Compare DecisionRecords between mock and real.
4. Enable real mode only in a staging Cloud Run service.
5. Validate Telegram real with a controlled internal bot/user.
6. Promote to production only after fallback, audit, and human review behavior
   are confirmed.
