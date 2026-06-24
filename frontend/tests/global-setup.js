const { execFileSync } = require("child_process");
const path = require("path");
const fs = require("fs");
const { TEST_DB_URL } = require("./e2e.constants");

// Seeds the isolated test database before the suite runs. Uses the backend's
// own venv + seed script so the schema and ORM stay the single source of truth.
module.exports = async () => {
  const backendDir = path.resolve(__dirname, "../../backend");
  const venvPython = path.join(backendDir, ".venv", "bin", "python");
  const python = fs.existsSync(venvPython) ? venvPython : "python3";

  execFileSync(python, ["scripts/seed_e2e.py"], {
    cwd: backendDir,
    env: {
      ...process.env,
      DATABASE_URL: TEST_DB_URL,
      // Ensure the `app` package is importable regardless of the script's dir.
      PYTHONPATH: backendDir,
    },
    stdio: "inherit",
  });
};
