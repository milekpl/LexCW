Playwright E2E tests for backup flows

Setup:

1. Install JS deps (from project root):

```bash
npm install
```

2. Install Playwright browsers:

```bash
npx playwright install
```

Run tests:

```bash
# Run the backup E2E test
npm run test:e2e
```

Notes:
- Tests assume the webapp is running and reachable at `http://127.0.0.1:5000`. Override with `BASE_URL` env var.
- The test `e2e/tests/backup.spec.js` exercises the create→validate→download flow and asserts the produced zip contains all required artifacts.
