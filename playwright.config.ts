import { defineConfig } from "@playwright/test";

const portalPort = process.env.PORTAL_PORT || "8090";
const portalBackendPort = process.env.PORTAL_BACKEND_BIND_PORT || "8091";
const baseURL = process.env.PORTAL_TEST_BASE_URL || `http://localhost:${portalPort}`;

export default defineConfig({
  testDir: "tests/playwright",
  timeout: 60_000,
  expect: { timeout: 25_000 },
  workers: 1,
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
  webServer: {
    command: "powershell -ExecutionPolicy Bypass -File ./scripts/start_portal_backend.ps1",
    url: baseURL,
    env: {
      PORTAL_PORT: portalPort,
      PORTAL_BACKEND_BIND_PORT: portalBackendPort,
    },
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
