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
VITE_AUTH_MODE=api_key
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
```

When `VITE_AUTH_MODE=api_key`, the app shows `/login` before the operations
panel. The API key is stored in localStorage and sent as:

```text
X-Admin-API-Key: <API key>
```

When `VITE_AUTH_MODE=firebase`, `/login` uses Firebase email/password auth and
API requests send:

```text
Authorization: Bearer <Firebase ID token>
```

Use `VITE_AUTH_MODE=disabled` or `VITE_REQUIRE_LOGIN=false` only for local
development when the backend is also running with local auth disabled.

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
/audit/shadow-decisions
/audit/shadow-decisions/:id
/tools/executions
/tools/executions/:id
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
4. Open `/login`, enter `ADMIN_API_KEY` in API-key mode or Firebase
   email/password in Firebase mode, and verify redirect to `/dashboard`.
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
24. Open `/audit/shadow-decisions` and verify the read-only `Evaluación IA` comparison table.
25. Open one IA evaluation detail and verify the summary, current-system section,
    IA-in-shadow section, human-readable differences, interpretation, and collapsed
    technical data.
26. Open `/tools/executions` and verify the `Acciones IA` table, filters, empty
    state, and error state.
27. Open one action detail, mark it as approved/rejected/needs_more_info/dismissed,
    add notes, and verify the saved message says the tool was not executed.
28. Refresh the detail page and verify the saved values are still present.
29. Click `Salir` and verify localStorage or the Firebase session is cleared and
    `/login` is shown.

## Cómo interpretar la Evaluación IA

`Evaluación IA` compares the decision actually used by the current system with
the decision proposed by the real IA running in shadow mode. The IA does not
answer customers and does not execute business actions.

- `Coinciden`: current system and IA propose the same core decision.
- `Hay diferencias`: IA proposes a different action, priority, pest type, or
  incident creation decision. Review whether the IA criterion is better.
- `Error de IA en sombra`: the IA could not be evaluated correctly. The current
  system was not affected.

The detail page keeps technical identifiers such as `trace_id`, raw differences,
and metadata inside `Datos técnicos`.

## Acciones IA

`Acciones IA` shows proposed tool calls from the controlled agent harness. It is
an operator review screen, not an execution console.

Operators can:

- inspect the proposed tool, provider, payload, risk level, and policy decision;
- approve, reject, request more information, or dismiss a proposal;
- add reviewer notes and an optional approved payload for future controlled
  execution.

Approving a proposal does not execute a tool by itself. For approved
`gmail.create_draft` records, the detail screen can show `Crear borrador en
Gmail`. That separate action creates a draft only when backend Gmail flags and
credentials are configured. It never sends email.

To create local sample records for QA:

```bash
make seed-tool-executions
```

Then open `/tools/executions` and review the seeded Gmail, Calendar, Telegram,
WhatsApp, and Firestore examples.

To prepare a Gmail draft action already approved for controlled execution:

```bash
SEED_APPROVED_GMAIL_DRAFT=true \
GMAIL_TEST_DRAFT_RECIPIENT=destino-controlado@example.test \
make seed-tool-executions
```

The `Crear borrador en Gmail` button appears only for approved
`gmail.create_draft` records that have not been executed yet. The backend must
also have `GMAIL_TOOLS_ENABLED=true` and `GMAIL_DRAFT_EXECUTION_ENABLED=true`.

## Dashboard Design System

The Hermes Pest Control dashboard follows a dark, high-density zinc SaaS theme (`zinc-900`, `zinc-950` with emerald accents). It is designed to be highly modular, responsive, and data-dense.

### Page Structure

Every premium page is wrapped inside the `DashboardShell` component. It provides the standard framework:
1. **SidebarNav**: Navigation panel on the left containing links to the operations, analytics, AI performance, and audit pages, alongside engine health signals.
2. **TopFiltersBar**: Cabecera block hosting global filters (Channel, Pest Type, Priority) and real-time refresh sync hooks.
3. **Main Content Band**: Where the page components are rendered.

### Reusable Components

All premium components live under `src/components/dashboard/`:
- **DashboardShell.vue**: The grid layout provider.
- **PageHeader.vue**: Unified header for displaying titles and descriptions.
- **SectionCard.vue**: Container component for widgets, charts, and lists.
- **KpiCard.vue**: Standard KPI cards with progress bar support.
- **FilterSelect.vue**: Customizable filter inputs.
- **DataToolbar.vue**: Layout component to align filters and list controls.
- **LoadingState.vue**: Pulse-spinner representing background sync.
- **EmptyState.vue**: Clean visual banner for empty lists.
- **ErrorBanner.vue**: Red-bordered dismissal banner for server exceptions.

### Rules of Dumb UI (Presentational vs Container)

To preserve architectural cleaness:
1. **No direct backend queries in components**: Dashboard subcomponents under `src/components/dashboard/` must remain presentational ("dumb"). They receive data via props and bubble events (`emit`) up for state actions.
2. **Container Pages**: Only files under `src/pages/` are allowed to manage asynchronous client API operations and store local state.
3. **No client recalculations**: Never compute priority thresholds or SLA timelines in the UI. Represent whatever strings and timestamps FastAPI resolves.

### How to Create New Vistas

To add a new premium page:
1. Add the path variables and conditional checks to `src/App.vue`.
2. Create a new Vue SFC under `src/pages/YourNewPage.vue`.
3. Wrap the content with `<DashboardShell>`:
   ```vue
   <script setup lang="ts">
   import DashboardShell from '../components/dashboard/DashboardShell.vue'
   import PageHeader from '../components/dashboard/PageHeader.vue'
   // ...
   </script>
   <template>
     <DashboardShell ...>
       <PageHeader title="New Vista" subtitle="..." />
       <!-- Use SectionCard, KpiCard, and other subcomponents -->
     </DashboardShell>
   </template>
   ```
4. Propagate navigate event to `App.vue` using `@navigate` emit.

