# Manual SMS alerts

Administrator-triggered SMS through Africa's Talking (AT). **Nothing is texted
automatically**: creating an alert, a new prediction, or a flood threshold never sends SMS.
The only path to a phone is an ADMIN calling `POST /api/v1/sms/test` or
`POST /api/v1/sms/broadcasts` with `confirm: true`.

## How it works

1. **Recipients** (`/alerts/subscribers`): a number is registered with explicit consent
   (checkbox + optional note). It can be texted only while *active*, *consented* and *not
   opted out*. Opt-out is kept as a record (not a delete), so a number cannot be silently
   re-added; re-subscribing needs fresh consent. Rows that pre-date consent tracking have no
   consent and are never texted.
2. **Compose → preview → confirm** (`/alerts/sms`): the preview shows the exact text, SMS
   parts and the (masked) recipient list. Sending requires ticking the confirmation, sends
   the recipient count the admin saw (a changed list is refused), and carries a one-time
   idempotency key.
3. **Test first**: a *test* goes to one registered, consenting number (yours). With a real
   provider, group broadcasts stay locked until `SMS_BROADCAST_ENABLED=true` **and** a real
   test has been *accepted* by the provider for that provider/environment.
4. **Records**: every attempt is stored (`sms_broadcasts`, `sms_messages`) before the
   provider is called. Per recipient: provider status/code, message ID, cost, submission
   time. **Submission ≠ delivery**: `delivery_status` stays `not_reported` until the
   provider's delivery-report callback arrives; it is never inferred.
5. **Failure honesty**: HTTP 4xx / rejected recipient → `failed`/`rejected` (nothing sent).
   Timeout, network error or HTTP 5xx → `unknown` (it may have been sent) and the same text
   is blocked from blind re-sending for `SMS_DUPLICATE_WINDOW_MINUTES`.
6. **Guards**: ADMIN-only; rate limits (3/min broadcasts, 5/min tests); recipient cap
   (`SMS_MAX_RECIPIENTS`); optional allowlist (`SMS_ALLOWED_NUMBERS`); same idempotency key →
   original result returned, no second send; same text + same recipients within the window →
   409.

## Setup

1. `alembic upgrade head` (adds `d8e3f6a92b57`: consent columns, `sms_broadcasts`, `sms_messages`).
2. Africa's Talking: create an account and an app. For the **sandbox** use username
   `sandbox` and the sandbox app's API key; sandbox messages go to AT's simulator, not real
   handsets. For **live** SMS use your live app username/key, top up credit, and register a
   sender ID. Zambian operators (MTN, Airtel, Zamtel) generally require sender-ID approval
   under ZICTA rules, and MTN does not accept unregistered alphanumeric IDs, so confirm with
   AT support which sender ID / shortcode to use for Zambia before relying on it.
3. Backend `.env` (see `.env.example`): `SMS_PROVIDER=africastalking`,
   `AFRICASTALKING_ENVIRONMENT`, `AFRICASTALKING_USERNAME`, `AFRICASTALKING_API_KEY`.
   Check `/alerts/sms`: it lists exactly what is missing.
4. Delivery reports / STOP replies (optional but needed for confirmed delivery): set
   `SMS_WEBHOOK_SECRET`, deploy the backend at a public HTTPS URL, and in the AT dashboard
   set the delivery-report callback to `/api/v1/sms/delivery-report?token=<secret>` and (needs
   an AT shortcode/number) the incoming-message callback to `/api/v1/sms/inbound?token=<secret>`.
   "Reply STOP to opt out." is appended to broadcasts only when the secret is set.
5. Register your own number with consent, send yourself a test, inspect the result, then
   (live only) set `SMS_BROADCAST_ENABLED=true`.

## Known limits

- Rate limiting is in-memory and per process (shared with the auth limiter).
- A crash between recording an attempt and the provider's reply leaves the record as
  `sending`; it is shown as such, never as success.
- Delivery-report field names and the accepted status codes (100/101/102) follow Africa's
  Talking's documented format as understood at build time; verify against a sandbox send.
- Messages are labelled `FloodShield DEMO` by default (`SMS_MESSAGE_PREFIX`): the model is
  research-grade and not validated for public warnings (docs/MODEL-EVALUATION.md).
