import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/playwright",
  timeout: 60_000,
  expect: { timeout: 25_000 },
  workers: 1,
  use: {
    baseURL: "http://localhost:8090",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "powershell -ExecutionPolicy Bypass -File ./scripts/start_portal_backend.ps1",
    url: "http://localhost:8090",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
