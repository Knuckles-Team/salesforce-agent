# Concept Registry — Salesforce Agent

> **Prefix**: `CONCEPT:SFDC-*`
> **Bridge**: `CONCEPT:ECO-4.0` (Unified Toolkit Ingestion)

## Project-Specific Concepts

| Concept ID | Name | Description |
|------------|------|-------------|
| `CONCEPT:SFDC-1.0` | Core REST Wrapper | Owned thin httpx client, typed error-envelope mapping, and the `Api` facade |
| `CONCEPT:SFDC-1.1` | OAuth2 Auth Flows | client-credentials, refresh-token, and JWT bearer flows with token cache, expiry refresh, and sandbox/production base URLs |
| `CONCEPT:SFDC-1.2` | Action-Routed Tool Surface | Five consolidated MCP tools (`soql`, `records`, `describe`, `bulk`, `admin`) shimming the resource clients |
| `CONCEPT:SFDC-1.3` | Safety Gates | `allow_destructive` gating for deletes, per-call query record caps, bulk result size caps, and secret redaction |
| `CONCEPT:SFDC-1.4` | Bulk API 2.0 Lifecycle | Ingest job create/upload/close/abort/status and capped CSV result downloads |
