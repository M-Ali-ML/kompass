// Shared configuration + fixture data for the Playwright E2E suite.
// The fixture strings must stay in sync with backend/scripts/seed_e2e.py.

const BACKEND_PORT = 8100;
const FRONTEND_PORT = 3100;

const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;
const COPILOTKIT_ENDPOINT = `${BACKEND_URL}/api/copilotkit`;

// Isolated SQLite database for tests so we never touch dev data.
const TEST_DB_PATH = "/tmp/kompass_e2e_test.db";
const TEST_DB_URL = `sqlite+aiosqlite:///${TEST_DB_PATH}`;

const FIXTURE = {
  greece: {
    title: "recommend a trip to greece in august",
    assistant: "ferry to Naxos",
  },
  japan: {
    title: "two weeks in japan",
    assistant: "JR Pass",
  },
};

module.exports = {
  BACKEND_PORT,
  FRONTEND_PORT,
  BACKEND_URL,
  FRONTEND_URL,
  COPILOTKIT_ENDPOINT,
  TEST_DB_PATH,
  TEST_DB_URL,
  FIXTURE,
};
