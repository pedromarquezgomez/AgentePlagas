# 09 Project Management For Codex

Development rules:

- Keep channel logic in adapters.
- Keep orchestration in services.
- Keep contracts in schemas.
- Keep environment configuration in `config/settings.py`.
- Update README when execution or architecture changes.
- Add tests when behavior becomes non-trivial.

Sprint discipline:

- Implement one vertical slice at a time.
- Verify with real local commands.
- Keep mocks replaceable through service abstractions.
- Avoid coupling Hermes, Firestore, and Telegram directly.

