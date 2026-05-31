#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  GOOGLE_CLOUD_PROJECT
  CLOUD_RUN_SERVICE
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required environment variable: ${var_name}" >&2
    exit 1
  fi
done

REGION="${REGION:-europe-west1}"
IMAGE_NAME="${IMAGE_NAME:-hermes-pest-control-backend}"
REPOSITORY="${ARTIFACT_REPOSITORY:-hermes}"
IMAGE_URI="${REGION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${REPOSITORY}/${IMAGE_NAME}:$(date +%Y%m%d%H%M%S)"

cat <<EOF
About to deploy backend to Cloud Run.

Project: ${GOOGLE_CLOUD_PROJECT}
Region:  ${REGION}
Service: ${CLOUD_RUN_SERVICE}
Image:   ${IMAGE_URI}

Required production configuration is passed separately with gcloud env vars or
Secret Manager. This script does not read or print tokens.
EOF

read -r -p "Continue? Type 'deploy' to proceed: " confirmation
if [[ "${confirmation}" != "deploy" ]]; then
  echo "Aborted."
  exit 1
fi

gcloud config set project "${GOOGLE_CLOUD_PROJECT}"
gcloud artifacts repositories describe "${REPOSITORY}" --location "${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Hermes container images"

gcloud builds submit backend --tag "${IMAGE_URI}"
gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image "${IMAGE_URI}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated
