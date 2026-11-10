import { defineConfig, devices } from "@playwright/test";

// Runs against the already-running stack (docker compose up):
//   frontend http://localhost:3000, API http://localhost:8000
// Point BASE_URL elsewhere to test another deployment.
export default defineConfig({
  testDir: "./e2e",
  // The suite registers real users and writes real predictions; one worker keeps
  // shared API/DB state predictable.
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.BASE_URL || "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
