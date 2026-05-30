.PHONY: dev test smoke set-telegram-webhook telegram-webhook-info

dev:
	cd backend && scripts/run_dev.sh

test:
	cd backend && scripts/run_tests.sh

smoke:
	cd backend && scripts/smoke_test.sh

set-telegram-webhook:
	cd backend && python scripts/set_telegram_webhook.py

telegram-webhook-info:
	cd backend && python scripts/get_telegram_webhook_info.py
