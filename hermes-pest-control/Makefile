.PHONY: dev test smoke evals evals-real evals-hermes-agent fake-hermes hermes-agent-server firestore-check set-telegram-webhook telegram-webhook-info frontend-install frontend-dev frontend-build

dev:
	cd backend && scripts/run_dev.sh

test:
	cd backend && scripts/run_tests.sh

smoke:
	cd backend && scripts/smoke_test.sh

evals:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python -m evals.run_evals

evals-real:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python -m evals.run_evals --hermes-mode real

evals-hermes-agent:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; HERMES_API_URL=$${HERMES_API_URL:-http://127.0.0.1:9100/agent} python -m evals.run_evals --hermes-mode real

fake-hermes:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/fake_hermes_server.py

hermes-agent-server:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/hermes_agent_server.py

firestore-check:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/check_firestore.py

set-telegram-webhook:
	cd backend && python scripts/set_telegram_webhook.py

telegram-webhook-info:
	cd backend && python scripts/get_telegram_webhook_info.py

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build
