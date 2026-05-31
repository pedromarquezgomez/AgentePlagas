# Hermes Frontend

Minimal Vue 3 + TypeScript + Vite operations panel with a dashboard, incident
views, human review queue, manual technician and visit management, and an
internal visit calendar. Google Calendar sync is optional and appears on visit
detail when the backend endpoint is available.

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

When `VITE_REQUIRE_LOGIN=true`, the app shows `/login` before the operations
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
/dashboard
/incidents
/incidents/:id
/human-review
/human-review/:id
/technicians
/technicians/:id
/visits
/visits/:id
/calendar
/documents
/documents/:id
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
4. Open `/login`, enter `ADMIN_API_KEY`, and verify redirect to `/dashboard`.
5. Open `/dashboard` and verify the summary cards link to each section, including calendar cards.
6. Open `/incidents` and verify the table, filters, empty state, and error state.
7. Click `Abrir` on one row.
8. Change status, priority, or internal notes.
9. Click `Guardar` and verify the success message.
10. Open `/human-review` and verify the queue, filters, empty state, and error state.
11. Click `Abrir` on one review item.
12. Change status, assigned operator, or resolution notes.
13. Click `Guardar` and verify the success message.
14. Open `/technicians`, create a technician, edit it, and verify the saved state.
15. Open `/visits`, create a visit, edit it, and verify the saved state.
16. Open a visit detail and verify the `Sincronización calendario` block.
17. Click `Sincronizar con calendario`; with backend sync disabled, verify the skipped message.
18. Open `/calendar`, switch between day and week views, filter by technician and status, and open a visit.
19. Open `/documents` and verify the documents table and filters.
20. Open an incident detail and click `Generar resumen de incidencia`.
21. Open a visit detail and click `Generar brief para técnico`.
22. Open a document detail, edit title/content/status, and save.
23. Open an incident detail and create a visit from `Visitas asociadas`.
24. Refresh the detail page and verify the saved values are still present.
25. Click `Salir` and verify localStorage is cleared and `/login` is shown.
