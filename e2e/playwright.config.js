// Playwright configuration for backup E2E tests
const { devices } = require('@playwright/test');

module.exports = {
  testDir: './tests',
  timeout: 60_000,
  expect: { timeout: 5000 },
  use: {
    headless: true,
    viewport: { width: 1280, height: 800 },
    actionTimeout: 5000,
    baseURL: process.env.BASE_URL || 'http://127.0.0.1:5000'
  }
};
