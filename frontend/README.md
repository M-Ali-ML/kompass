# Kompass Frontend

Next.js 16 / React 19 client for Kompass — chat-driven trip planning with
CopilotKit v2 generative UI, an interactive Google Map, and Tailwind CSS v4.

See the [root README](../README.md) for full setup, environment variables, and
test instructions. Quick start:

```bash
npm install
cp .env.example .env.local   # add your Google Maps key
npm run dev                  # http://localhost:3000 (backend expected on :8000)
```

Scripts:

* `npm run dev` / `npm run build` / `npm run start`
* `npm run lint` — ESLint
* `npm run test:unit` — Vitest unit tests
* `npm run test:e2e` — Playwright E2E (boots both servers on isolated ports)
