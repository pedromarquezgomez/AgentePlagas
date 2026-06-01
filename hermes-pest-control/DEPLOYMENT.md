# Production Deployment

Hermes Pest Control System is prepared for this production shape:

```text
Firebase Hosting
  -> Vue operations panel
  -> Cloud Run FastAPI backend
  -> Firestore
  -> Firebase Auth

Telegram / WhatsApp
  -> Cloud Run webhooks
  -> channel adapters
  -> ConversationService
```

Region preference: `europe-west1`.

Current Firebase project:

```text
Project ID: control-plagas-ai
Project number: 601698914613
Hosting URL: https://control-plagas-ai.web.app
Default hosting site: control-plagas-ai
```

## Production Pilot Status

V1 is deployed and operating as a production pilot.

Production URLs:

```text
Frontend: https://control-plagas-ai.web.app
Backend:  https://hermes-pest-control-backend-601698914613.europe-west1.run.app
Telegram webhook: https://hermes-pest-control-backend-601698914613.europe-west1.run.app/webhooks/telegram
```

Validated production state:

- Firebase Auth login works.
- Frontend sends Firebase Bearer ID tokens.
- Backend validates Firebase Auth.
- Firestore real is operational.
- Telegram real creates incidents.
- The panel shows incidents created from Telegram.
- CORS allows `https://control-plagas-ai.web.app`.
- `HERMES_MODE=mock` remains active for V1.

See [V1_PRODUCTION_PILOT.md](./V1_PRODUCTION_PILOT.md) for the closure report,
manual validation checklist, risks, and next recommended phase.

## Prerequisites

- Google Cloud project with billing enabled.
- Firebase project linked to the Google Cloud project.
- Firestore enabled.
- Firebase Auth enabled.
- Artifact Registry API, Cloud Build API, Cloud Run API, and Firebase Hosting enabled.
- `gcloud` authenticated locally.
- Firebase CLI authenticated locally.

Never commit `.env`, service account JSON files, access tokens, API keys, or
private keys.

## Backend Production Variables

Minimum production configuration:

```bash
APP_ENV=production
AUTH_MODE=firebase
FIREBASE_AUTH_ENABLED=true
FIREBASE_PROJECT_ID=control-plagas-ai
CORS_ALLOWED_ORIGINS=https://control-plagas-ai.web.app
FRONTEND_PUBLIC_URL=https://control-plagas-ai.web.app
HERMES_MODE=mock
```

Firestore credentials:

- Preferred on Cloud Run: use the runtime service account with Firestore
  permissions and set `FIREBASE_PROJECT_ID`.
- Alternative: set `FIREBASE_CREDENTIALS_JSON` through Secret Manager.
- Local fallback only: `FIREBASE_CREDENTIALS_PATH=/absolute/path/to/key.json`.

Optional production variables:

```bash
HERMES_MODE=real
HERMES_API_URL=
HERMES_API_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
WHATSAPP_ENABLED=false
WHATSAPP_PROVIDER=meta
WHATSAPP_VERIFY_TOKEN=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_WEBHOOK_SECRET=
WHATSAPP_GRAPH_API_VERSION=v20.0
GOOGLE_CALENDAR_ENABLED=false
GOOGLE_CALENDAR_ID=
GOOGLE_CALENDAR_CREDENTIALS_JSON=
```

Security rules:

- Do not use `AUTH_MODE=disabled` in production.
- Do not use Firestore mock in production.
- Do not use wildcard CORS origins in production.
- Keep `/messages/test` unavailable in production.
- Keep `HERMES_MODE=mock` for the V1 production pilot. Do not enable the LLM
  agent in production until controlled evals, `/messages/test`, DecisionRecords,
  fallback, and HumanReview behavior have been reviewed.

## Backend Deploy

The backend Dockerfile is Cloud Run-ready and listens on the `PORT` environment
variable.

Manual build and deploy:

```bash
export GOOGLE_CLOUD_PROJECT=<project-id>
export CLOUD_RUN_SERVICE=hermes-pest-control-backend
export REGION=europe-west1
scripts/deploy_backend_cloud_run.sh
```

For this project:

```bash
export GOOGLE_CLOUD_PROJECT=control-plagas-ai
export CLOUD_RUN_SERVICE=hermes-pest-control-backend
export REGION=europe-west1
scripts/deploy_backend_cloud_run.sh
```

The script builds and deploys the container, but production environment
variables should be configured separately with `gcloud run services update`,
Cloud Run UI, or Secret Manager.

Cloud Build is also available:

```bash
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions _REGION=europe-west1,_SERVICE_NAME=hermes-pest-control-backend
```

Example Cloud Run env update:

```bash
gcloud run services update hermes-pest-control-backend \
  --region europe-west1 \
  --set-env-vars APP_ENV=production,AUTH_MODE=firebase,FIREBASE_AUTH_ENABLED=true,FIREBASE_PROJECT_ID=control-plagas-ai,CORS_ALLOWED_ORIGINS=https://control-plagas-ai.web.app,FRONTEND_PUBLIC_URL=https://control-plagas-ai.web.app,HERMES_MODE=mock,WHATSAPP_ENABLED=false,GOOGLE_CALENDAR_ENABLED=false
```

Use Secret Manager for channel tokens and API keys.

## Frontend Deploy

Create a local frontend production env:

```bash
cd frontend
cp .env.example .env.production
```

Set:

```bash
VITE_API_BASE_URL=https://<cloud-run-url>
VITE_AUTH_MODE=firebase
VITE_FIREBASE_API_KEY=<firebase-web-api-key>
VITE_FIREBASE_AUTH_DOMAIN=control-plagas-ai.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=control-plagas-ai
```

Build and deploy:

```bash
npm run build
firebase deploy --only hosting
```

Or from the repository root:

```bash
export FIREBASE_PROJECT_ID=control-plagas-ai
scripts/deploy_frontend_firebase.sh
```

`firebase.json` serves `frontend/dist` and rewrites SPA routes to
`index.html`.

## Firebase Auth Setup

1. Open Firebase Console.
2. Enable Authentication.
3. Enable Email/Password provider.
4. Create the first admin user manually.
5. Add the Firebase Hosting domain to authorized domains.
6. Ensure the frontend uses `VITE_AUTH_MODE=firebase`.

Roles and multi-company permissions are not implemented yet.

## Webhooks

Telegram production webhook:

```text
https://hermes-pest-control-backend-601698914613.europe-west1.run.app/webhooks/telegram
```

Configure with:

```bash
export TELEGRAM_BOT_TOKEN=<token>
export TELEGRAM_WEBHOOK_SECRET=<optional-secret>
export CLOUD_RUN_URL=https://hermes-pest-control-backend-601698914613.europe-west1.run.app
scripts/set_production_telegram_webhook.sh
```

WhatsApp production webhook:

```text
https://<cloud-run-url>/webhooks/whatsapp
```

Configure this URL in Meta Developer Console. Use
`WHATSAPP_VERIFY_TOKEN` for webhook verification and `WHATSAPP_WEBHOOK_SECRET`
for the optional internal header check if your gateway supports it.

## Hermes Agent LLM Cloud Run Service

The LLM wrapper can be deployed as a separate Cloud Run service:

```text
Service: hermes-agent-llm
Region: europe-west1
Project: control-plagas-ai
URL: https://hermes-agent-llm-601698914613.europe-west1.run.app
```

Deploy:

```bash
export GOOGLE_CLOUD_PROJECT=control-plagas-ai
export REGION=europe-west1
export CLOUD_RUN_SERVICE=hermes-agent-llm
scripts/deploy_hermes_agent_llm_cloud_run.sh
```

The script builds `backend/Dockerfile.agent` and deploys only the wrapper. It
does not enable shadow mode in the main backend.

Required wrapper configuration:

```bash
HERMES_AGENT_MODE=llm
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=30
AGENT_MAX_OUTPUT_TOKENS=800
AGENT_TEMPERATURE=0
HERMES_SKILLS_DIR=/app/hermes/skills
```

Secrets should be provided through Secret Manager:

```text
OPENAI_API_KEY
HERMES_AGENT_API_KEY
```

Default Secret Manager names used by the deploy script:

```text
openai-api-key
hermes-agent-api-key
```

Create them without printing values:

```bash
printf '%s' '<openai-api-key>' \
  | gcloud secrets create openai-api-key \
      --project control-plagas-ai \
      --data-file=-

openssl rand -base64 32 \
  | gcloud secrets create hermes-agent-api-key \
      --project control-plagas-ai \
      --data-file=-
```

Grant the Cloud Run runtime service account access only to those secrets:

```bash
PROJECT_NUMBER="$(gcloud projects describe control-plagas-ai --format='value(projectNumber)')"
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud secrets add-iam-policy-binding openai-api-key \
  --project control-plagas-ai \
  --member "serviceAccount:${SERVICE_ACCOUNT}" \
  --role roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding hermes-agent-api-key \
  --project control-plagas-ai \
  --member "serviceAccount:${SERVICE_ACCOUNT}" \
  --role roles/secretmanager.secretAccessor
```

The wrapper accepts:

```text
GET /health
POST /agent
```

If `HERMES_AGENT_API_KEY` is configured, `POST /agent` requires:

```text
X-Hermes-Agent-Key: <secret>
```

The main backend can later be configured manually with:

```bash
HERMES_MODE=mock
HERMES_SHADOW_MODE=true
HERMES_SHADOW_API_URL=https://<hermes-agent-llm-url>/agent
HERMES_SHADOW_API_KEY=<secret>
HERMES_SHADOW_SAMPLE_RATE=0.1
HERMES_SHADOW_TIMEOUT_SECONDS=20
```

Do not apply those main-backend variables until the controlled shadow pilot is
approved.

## Readiness

Public safe probes:

```bash
curl https://<cloud-run-url>/health
curl https://<cloud-run-url>/ready
curl https://<cloud-run-url>/config/status
```

`/ready` reports safe status only:

- `app_env`
- `firestore_mode`
- `auth_mode`
- readiness booleans
- degraded reasons

It does not write to Firestore and does not expose secrets.

## Post-Deploy Checklist

1. `GET /health` returns `{"status":"ok"}`.
2. `GET /ready` returns `status=ready`.
3. `GET /config/status` does not expose tokens or credentials.
4. Frontend loads from Firebase Hosting.
5. Firebase Auth login works.
6. `/messages/test` is unavailable when `APP_ENV=production`.
7. Telegram webhook points to Cloud Run.
8. WhatsApp webhook verifies successfully if enabled.
9. Send a real Telegram message and confirm a bot response.
10. Test WhatsApp with mock/sandbox or Meta real configuration.
11. Create an incident and verify it appears on the dashboard.
12. Confirm Firestore collections receive documents.
13. Confirm decision audit records are created.

## Rollback

Backend:

```bash
gcloud run revisions list --service hermes-pest-control-backend --region europe-west1
gcloud run services update-traffic hermes-pest-control-backend \
  --region europe-west1 \
  --to-revisions <previous-revision>=100
```

Frontend:

```bash
firebase hosting:releases:list
firebase hosting:rollback
```

## Known Risks

- Firebase Auth has no roles yet.
- `AUTH_MODE=api_key` is still supported for compatibility but should not be
  preferred for production panel users.
- Google Calendar sync is optional and manual.
- WhatsApp production behavior depends on Meta app review and webhook settings.
- Hermes real mode should be rolled out behind evaluation and fallback checks.
- Hermes shadow mode is disabled by default. If enabled for a controlled pilot,
  confirm `HERMES_SHADOW_API_URL`, sample rate, and logs before routing any
  meaningful traffic. Shadow decisions must remain audit-only and must not
  affect customer replies or business writes.
