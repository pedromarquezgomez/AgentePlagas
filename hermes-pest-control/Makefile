.PHONY: dev test smoke smoke-llm evals evals-real evals-hermes-agent evals-agent-llm synthetic-cases synthetic-shadow-eval synthetic-shadow-eval-cloud seed-tool-executions gmail-draft-check fake-hermes hermes-agent-server hermes-agent-llm firestore-check set-telegram-webhook telegram-webhook-info frontend-install frontend-dev frontend-build

dev:
	cd backend && scripts/run_dev.sh

test:
	cd backend && scripts/run_tests.sh

smoke:
	cd backend && scripts/smoke_test.sh

smoke-llm:
	cd backend && scripts/smoke_test_llm.sh

evals:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python -m evals.run_evals

evals-real:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python -m evals.run_evals --hermes-mode real

evals-hermes-agent:
	@curl -fsS $${HERMES_AGENT_HEALTH_URL:-http://127.0.0.1:9100/health} >/dev/null || (echo "Hermes Agent server is not reachable. Start it first with: make hermes-agent-server" && exit 1)
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; HERMES_API_URL=$${HERMES_API_URL:-http://127.0.0.1:9100/agent} python -m evals.run_evals --hermes-mode real

evals-agent-llm:
	@curl -fsS $${HERMES_AGENT_HEALTH_URL:-http://127.0.0.1:9100/health} >/dev/null || (echo "Hermes LLM agent is not reachable. Start it first in another terminal with: make hermes-agent-llm" && exit 1)
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; HERMES_API_URL=$${HERMES_API_URL:-http://127.0.0.1:9100/agent} python -m evals.run_evals --hermes-mode real

synthetic-cases:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python -m evals.synthetic.generate_synthetic_cases

synthetic-shadow-eval:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; APP_ENV=test AGENT_PROVIDER=mock python -m evals.synthetic.run_synthetic_shadow_eval

synthetic-shadow-eval-cloud:
	@test -n "$$HERMES_SHADOW_API_URL" || (echo "Set HERMES_SHADOW_API_URL explicitly before running cloud synthetic shadow eval." && exit 1)
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; APP_ENV=test python -m evals.synthetic.run_synthetic_shadow_eval

seed-tool-executions:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/seed_tool_execution_records.py

gmail-draft-check:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/check_gmail_draft.py

fake-hermes:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/fake_hermes_server.py

hermes-agent-server:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; python scripts/hermes_agent_server.py

hermes-agent-llm:
	cd backend && if [ -f .venv/bin/activate ]; then . .venv/bin/activate; fi; HERMES_AGENT_MODE=llm python scripts/hermes_agent_server.py

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

nous-dashboard:
	@echo "Preparando el Dashboard nativo de Nous Research Hermes Agent..."
	@if [ ! -d backend/nous-hermes-agent ]; then \
		echo "Clonando el repositorio oficial de hermes-agent..."; \
		git clone --depth 1 https://github.com/nousresearch/hermes-agent.git backend/nous-hermes-agent; \
	fi
	@if [ ! -d backend/nous-hermes-agent/.venv-dashboard ]; then \
		echo "Creando entorno virtual e instalando dependencias de hermes-agent..."; \
		python3 -m venv backend/nous-hermes-agent/.venv-dashboard && \
		backend/nous-hermes-agent/.venv-dashboard/bin/pip install --upgrade pip && \
		backend/nous-hermes-agent/.venv-dashboard/bin/pip install -e backend/nous-hermes-agent; \
	fi
	@echo "Conectando las Skills del proyecto al archivo de configuración de Hermes..."
	@backend/nous-hermes-agent/.venv-dashboard/bin/python backend/scripts/connect_nous_skills.py
	@echo "Iniciando el Dashboard nativo de Nous Research (http://127.0.0.1:9119)..."
	@OPENAI_API_KEY="$$(gcloud secrets versions access latest --secret="openai-api-key" 2>/dev/null || echo "$$OPENAI_API_KEY")" \
	backend/nous-hermes-agent/.venv-dashboard/bin/hermes dashboard

