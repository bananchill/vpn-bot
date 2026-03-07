import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5173',
    viewport: { width: 375, height: 812 },
    screenshot: 'on',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev -- --port 5173',
    port: 5173,
    reuseExistingServer: true,
    timeout: 15000,
  },
  projects: [
    { name: 'mobile', use: { browserName: 'chromium' } },
  ],
});
