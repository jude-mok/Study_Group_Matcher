# Study Matcher web

React + TypeScript web client for the existing Study Group Matcher team project.
The original Flutter client stays in `../frontend`; the existing API stays in
`../backend`. This is a continuation of the team repository, not a new project.

## Run

Use Node 24 or newer.

```sh
cd web
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Select **Explore the demo** to use the sample
workspace without a server or account. Data is held in memory and resets on
refresh/exit. Demo chat is local, not a conversation with real users. Example
match scores are illustrative and are not recomputed when editing preferences.

For an existing API, copy `.env.example` to `.env.local` and set
`VITE_API_URL=http://127.0.0.1:8000`. Restart Vite after changing environment
variables. The API must allow `http://127.0.0.1:5173` in `CORS_ORIGINS`.

## Implemented web flows

- Landing page, sign-in and registration forms, explicit demo/account modes.
- Overview, recommendations with score explanations, search and course filter.
- Course enrollment/removal; group creation and immediate joining (matching the
  current backend, whose behavior has diverged from its older approval-flow docs).
- Group chat and member list; browser-native WebSocket, reconnect/backoff,
  history recovery and message deduplication, older-message pagination.
- Meeting proposals/votes and group/personal calendar; add/delete plans.
- Study preferences, per-tab account sessions and coordinated token refresh.
- Responsive desktop/mobile navigation, labeled controls and modal focus handling.

Live mutations await the API response; sample data is never substituted for a
failed real request. Signing out clears this tab's session. Server-wide token
revocation is not implemented by this client. A message is rendered after the
server echo; durable outbound message retry/acknowledgement remains future work.

## Checks

```sh
npm test
npm run build
```

The tests cover enrollment/recommendation changes, group/chat creation, duplicate
joining, unanimous voting/calendar creation, demo isolation, chat deduplication,
time validation, concurrent token refresh, sign-out races, rejected refresh,
network failures, and validation/empty-response handling. GitHub Actions runs
the tests and production build for web changes.

These checks do not assert that the existing live Supabase database is ready.
The web client uses the backend schemas but must still be validated against a
dedicated non-production database with two test users before live release.

For Vercel, use `web` as the project root, `npm run build` as the build command,
and `dist` as the output directory. Set `VITE_API_URL` to the live backend origin
and allow the web origin in backend `CORS_ORIGINS` when enabling live accounts.

### Original app view

The Web / App switch runs the original Flutter widgets in a same-origin iframe. Both views remain mounted when switching, preserving their separate demo states. App sample data is in memory and resets on refresh; there are no real API calls or cross-view account/data synchronization.

`public/app-version/` contains the static Flutter build so Vercel needs only Node. Regenerate after changing Flutter screens from the repository root:

```sh
FLUTTER_BIN=/path/to/flutter/bin/flutter python3 web/scripts/build-app-preview.py
```

The script copies Flutter sources to a temporary directory, substitutes local demo transports, and builds the actual screens. It does not edit the original mobile sources. Keep regenerated assets with the web deployment. Existing unfinished mobile features remain as in the original app; this is not a live multiuser backend. Vercel allows same-origin framing for this view.

Production builds load the public API address from `.env.production`. This file
contains no credentials. Vercel environment variables can override this value.

### Password recovery

The sign-in dialog includes **Forgot password?**. The recovery page works even
when an ordinary app session is already active. Recovery credentials are read
from the Supabase implicit-flow fragment, removed from the URL immediately, and
kept only in memory; reloading requires reopening/requesting a recovery link.

Deployment setup:
1. Set backend `PASSWORD_RESET_REDIRECT_URL` to `https://YOUR_WEB_HOST/?reset=1`.
2. Add that exact URL under Supabase Authentication → URL Configuration → Redirect URLs.
3. Keep the Reset Password email link using `{{ .ConfirmationURL }}`. This
   implementation uses the backend SDK's default implicit flow, not PKCE or a
   custom token-hash email template.
4. Keep `VITE_API_URL` pointing to the backend and allow the web origin in CORS.

If no redirect override is set, Supabase's configured Site URL is used. Before
release, verify actual email delivery and click-through using a test account.
The automated tests use fake credentials and do not send real emails.
