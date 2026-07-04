# Concept Registry — Salesforce Agent

> **Prefix**: `CONCEPT:SFDC-*`
> **Bridge**: `CONCEPT:AU-ECO.messaging.native-backend-abstraction` (Unified Toolkit Ingestion)

## Project-Specific Concepts

| Concept ID | Name | Description |
|------------|------|-------------|
| `CONCEPT:SF-OS.governance.sfdc` | Core REST Wrapper | Owned thin httpx client, typed error-envelope mapping, and the `Api` facade |
| `CONCEPT:SF-OS.identity.sfdc` | OAuth2 Auth Flows | client-credentials, refresh-token, and JWT bearer flows with token cache, expiry refresh, and sandbox/production base URLs |
| `CONCEPT:SF-OS.governance.sfdc-2` | Action-Routed Tool Surface | Five consolidated MCP tools (`soql`, `records`, `describe`, `bulk`, `admin`) shimming the resource clients |
| `CONCEPT:SF-OS.governance.destructive-operations-delete-collections` | Safety Gates | `allow_destructive` gating for deletes, per-call query record caps, bulk result size caps, and secret redaction |
| `CONCEPT:SF-OS.governance.sfdc-3` | Bulk API 2.0 Lifecycle | Ingest job create/upload/close/abort/status and capped CSV result downloads |
