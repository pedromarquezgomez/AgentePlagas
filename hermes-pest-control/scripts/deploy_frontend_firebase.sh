#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${FIREBASE_PROJECT_ID:-}" ]]; then
  echo "Missing required environment variable: FIREBASE_PROJECT_ID" >&2
  exit 1
fi

cat <<EOF
About to deploy frontend to Firebase Hosting.

Firebase project: ${FIREBASE_PROJECT_ID}

The build uses frontend/.env or exported VITE_* variables. This script does not
print Firebase web config values.
EOF

read -r -p "Continue? Type 'deploy' to proceed: " confirmation
if [[ "${confirmation}" != "deploy" ]]; then
  echo "Aborted."
  exit 1
fi

(cd frontend && npm install && npm run build)
firebase deploy --project "${FIREBASE_PROJECT_ID}" --only hosting
