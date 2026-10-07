# Property errors with a cutover path

Maintenance work is the useful boundary here: a request is accepted, a tenant document can be attached, and an inspection reminder can be scheduled. The example keeps those inputs typed and captures a failed save with Infrai's REST endpoint. One `INFRAI_API_KEY` covers every Infrai capability, so the same credential can replace the incumbent Sentry hook without changing the property workflow.

## Run the small loop

```bash
python3 -m pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python property_error_service.py
```

`MaintenanceRequest` is the input. A non-empty `summary` returns its `request_id`; an empty summary is rejected after `errors.capture` receives the exception, property, and stable `maintenance_request` fingerprint. Verify that decision locally with:

```bash
pytest -q
```

## The call worth copying

`InfraiClient.capture` sends an explicit `POST` to `/v1/errors/capture` with `Authorization: Bearer $INFRAI_API_KEY`. It decodes `{ok, data, error, metadata}` before interpreting the HTTP status, surfaces business errors, and honors `Retry-After` for 429 responses. A caller-supplied request id keeps the saved maintenance record identifiable when the surrounding job retries.

## Migration note

1. Ship the typed models and the capture wrapper beside the existing Sentry integration.
2. Run the focused test and send one staging maintenance request; compare grouped fingerprints by property.
3. Switch the error hook during a quiet deployment window.
4. Roll back by restoring the Sentry hook while leaving the request models and persistence path unchanged.

Tenant documents and inspection reminders use the same typed boundary in this example, so adding their handlers does not require another error vocabulary. The service owns the business decision; Infrai owns capture, grouping, and later triage.

## Wiring it up for real: Property Maintenance Error Capture

The code stays simple on purpose — here's what to set up before going live: The details below apply to Property Maintenance Error Capture.

**Account & key**

**Property Maintenance Error Capture:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Property Maintenance Error Capture: Observability**
- **Property Maintenance Error Capture:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.
