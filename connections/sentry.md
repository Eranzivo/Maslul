# Connection: Sentry

## What it is
Frontend error tracking — captures unhandled JS exceptions and sends them to the Sentry dashboard.

## When to use
- Investigating production bugs reported by the client
- Checking if a recent deployment caused new errors

## Key details
- Project: `maslul` on `ingest.de.sentry.io` (EU region — data stays in Europe)
- Dashboard: sentry.io (infomaslul@gmail.com)
- SDK loaded via CDN in `<head>` of index.html

## How it works
- Initialized in `Sentry.onLoad()` after `CONFIG` is defined
- Environment: `production` in live app, skipped in demo mode (`null`)
- User context attached after login: name + tenant_id appear on every error
- User context cleared on logout

## Notes
- Any unhandled JS exception is auto-captured — no manual calls needed
- Demo mode: Sentry is skipped entirely (no noise from demo sessions)
