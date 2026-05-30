# 01 Channel Agnostic Messaging

All channels must produce an `IncomingMessage` before reaching business logic.

Required normalized fields:

- `channel`
- `external_user_id`
- `external_chat_id`
- `message_type`
- `text`
- `attachments`
- `metadata`

Guidelines:

- Preserve original provider details only in `metadata`.
- Keep provider identifiers as strings.
- Do not leak Telegram-specific naming into services.
- Outbound messages use `OutgoingMessage` before returning to any adapter.

