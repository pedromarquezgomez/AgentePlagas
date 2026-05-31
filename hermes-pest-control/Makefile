.PHONY: dev test smoke evals set-telegram-webhook telegram-webhook-info frontend-install frontend-dev frontend-build

dev:
	cd backend && scripts/run_dev.sh

test:
	cd backend && scripts/run_tests.sh

smoke:
	cd backend && scripts/smoke_test.sh

evals:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python -m evals.run_evals

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
