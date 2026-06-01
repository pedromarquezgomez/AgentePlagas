#!/usr/bin/env bash
set -euo pipefail

GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-control-plagas-ai}"
REGION="${REGION:-europe-west1}"
CLOUD_RUN_SERVICE="${HERMES_AGENT_SERVICE:-${CLOUD_RUN_SERVICE:-hermes-agent-llm}}"
IMAGE_NAME="${IMAGE_NAME:-hermes-agent-llm}"
REPOSITORY="${ARTIFACT_REPOSITORY:-hermes}"
OPENAI_MODEL="${OPENAI_MODEL:-gpt-4.1-mini}"
OPENAI_TIMEOUT_SECONDS="${OPENAI_TIMEOUT_SECONDS:-30}"
AGENT_MAX_OUTPUT_TOKENS="${AGENT_MAX_OUTPUT_TOKENS:-800}"
AGENT_TEMPERATURE="${AGENT_TEMPERATURE:-0}"
HERMES_SKILLS_DIR="${HERMES_SKILLS_DIR:-/app/hermes/skills}"
HERMES_AGENT_API_KEY_SECRET="${HERMES_AGENT_API_KEY_SECRET:-hermes-agent-api-key:latest}"
OPENAI_API_KEY_SECRET="${OPENAI_API_KEY_SECRET:-openai-api-key:latest}"
IMAGE_URI="${REGION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${REPOSITORY}/${IMAGE_NAME}:$(date +%Y%m%d%H%M%S)"
TMP_CLOUDBUILD="$(mktemp)"
cleanup() {
  rm -f "${TMP_CLOUDBUILD}"
}
trap cleanup EXIT

cat <<EOF
About to deploy Hermes Agent LLM wrapper to Cloud Run.

Project: ${GOOGLE_CLOUD_PROJECT}
Region:  ${REGION}
Service: ${CLOUD_RUN_SERVICE}
Image:   ${IMAGE_URI}

Secrets are referenced by name only:
- OPENAI_API_KEY: ${OPENAI_API_KEY_SECRET}
- HERMES_AGENT_API_KEY: ${HERMES_AGENT_API_KEY_SECRET}

This script does not print secret values and does not enable shadow mode on the
main backend.
EOF

read -r -p "Continue? Type 'deploy-agent' to proceed: " confirmation
if [[ "${confirmation}" != "deploy-agent" ]]; then
  echo "Aborted."
  exit 1
fi

gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
if ! gcloud secrets describe "${OPENAI_API_KEY_SECRET%%:*}" --project "${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
  echo "Missing Secret Manager secret: ${OPENAI_API_KEY_SECRET%%:*}" >&2
  echo "Create it without printing the value, for example:" >&2
  echo "  printf '%s' '<openai-api-key>' | gcloud secrets create ${OPENAI_API_KEY_SECRET%%:*} --project ${GOOGLE_CLOUD_PROJECT} --data-file=-" >&2
  exit 1
fi

if ! gcloud secrets describe "${HERMES_AGENT_API_KEY_SECRET%%:*}" --project "${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
  echo "Missing Secret Manager secret: ${HERMES_AGENT_API_KEY_SECRET%%:*}" >&2
  echo "Create it without printing the value, for example:" >&2
  echo "  openssl rand -base64 32 | gcloud secrets create ${HERMES_AGENT_API_KEY_SECRET%%:*} --project ${GOOGLE_CLOUD_PROJECT} --data-file=-" >&2
  exit 1
fi

gcloud artifacts repositories describe "${REPOSITORY}" --location "${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Hermes container images"

cat >"${TMP_CLOUDBUILD}" <<EOF
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - -f
      - backend/Dockerfile.agent
      - -t
      - ${IMAGE_URI}
      - .
images:
  - ${IMAGE_URI}
EOF

gcloud builds submit . --config "${TMP_CLOUDBUILD}"

gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image "${IMAGE_URI}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "HERMES_AGENT_MODE=llm,LLM_PROVIDER=openai,OPENAI_MODEL=${OPENAI_MODEL},OPENAI_TIMEOUT_SECONDS=${OPENAI_TIMEOUT_SECONDS},AGENT_MAX_OUTPUT_TOKENS=${AGENT_MAX_OUTPUT_TOKENS},AGENT_TEMPERATURE=${AGENT_TEMPERATURE},HERMES_SKILLS_DIR=${HERMES_SKILLS_DIR}" \
  --set-secrets "OPENAI_API_KEY=${OPENAI_API_KEY_SECRET},HERMES_AGENT_API_KEY=${HERMES_AGENT_API_KEY_SECRET}"

cat <<EOF

Deployment requested.

Health check:
curl https://<hermes-agent-llm-url>/health

Main backend shadow configuration is still manual and should remain disabled
until the controlled pilot gate is approved.
EOF
