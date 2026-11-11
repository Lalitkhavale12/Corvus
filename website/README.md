# Corvus Clinical Console

React 19 + Vite front end for the Corvus CKD screening API. Eleven pages: dashboard,
assessment, result, prediction history, patient and doctor profiles, model comparison.

## Running it

In normal use the SPA is served by nginx from Compose (port 3000) - see the root
`README.md` for the full stack. For front-end work only:

```bash
npm install
npm run dev     # http://localhost:5173
npm run e2e     # Playwright, needs the Compose stack up
npm run lint    # oxlint
```

`VITE_API_URL` (see `.env.example`) is baked in at build time and defaults to
`http://localhost:8000`. The E2E specs in `e2e/` drive the real containers rather than
a mock, so start the stack first or `npm run e2e` will fail at login.

Screening aid only, not a diagnosis.
