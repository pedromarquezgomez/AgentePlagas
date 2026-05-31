# Hermes Frontend

Minimal Vue 3 + TypeScript + Vite panel for viewing and updating pest control incidents.

## Install

```bash
cd frontend
npm install
cp .env.example .env
```

## Configure

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_REQUIRE_LOGIN=true
```

When `VITE_REQUIRE_LOGIN=true`, the app shows `/login` before the incidents
panel. The API key is stored in localStorage and sent as:

```text
X-Admin-API-Key: <API key>
```

Use `VITE_REQUIRE_LOGIN=false` only for local development when the backend has
`REQUIRE_ADMIN_AUTH=false`.

## Run

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:5173/incidents
```

Available paths:

```text
/incidents
/incidents/:id
/login
```

## Build

```bash
npm run build
```

## Test Manually

1. Start the FastAPI backend.
2. Create at least one incident through `/messages/test` or Telegram.
3. Start the frontend with `npm run dev`.
4. Open `/login`, enter `ADMIN_API_KEY`, and verify redirect to `/incidents`.
5. Open `/incidents` and verify the table, filters, empty state, and error state.
6. Click `Abrir` on one row.
7. Change status, priority, or internal notes.
8. Click `Guardar` and verify the success message.
9. Refresh the detail page and verify the saved values are still present.
10. Click `Salir` and verify localStorage is cleared and `/login` is shown.
