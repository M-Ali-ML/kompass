const { defineConfig, devices } = require('@playwright/test');
const path = require('path');
const {
  BACKEND_PORT,
  FRONTEND_PORT,
  BACKEND_URL,
  FRONTEND_URL,
  COPILOTKIT_ENDPOINT,
  TEST_DB_URL,
} = require('./tests/e2e.constants');

const backendDir = path.resolve(__dirname, '../backend');

module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['line'], ['html', { open: 'never' }]],
  globalSetup: require.resolve('./tests/global-setup.js'),
  use: {
    baseURL: FRONTEND_URL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Backend API on an isolated DB, started from its own venv.
      command: `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
      cwd: backendDir,
      url: `${BACKEND_URL}/health`,
      timeout: 60_000,
      reuseExistingServer: !process.env.CI,
      env: { DATABASE_URL: TEST_DB_URL },
    },
    {
      // Production build + start pointed at the test backend. We build (rather
      // than `next dev`) because NEXT_PUBLIC_* is inlined at build time, which
      // reliably bakes the test endpoint; an isolated distDir keeps this from
      // touching a developer's `.next` / dev-server lock.
      command: `npm run build && npm run start -- --port ${FRONTEND_PORT} --hostname 127.0.0.1`,
      url: FRONTEND_URL,
      timeout: 180_000,
      reuseExistingServer: !process.env.CI,
      env: {
        NEXT_PUBLIC_COPILOTKIT_ENDPOINT: COPILOTKIT_ENDPOINT,
        NEXT_DIST_DIR: '.next-e2e',
      },
    },
  ],
});
