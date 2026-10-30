# CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001` | `tests/test_default_content_surfaces.py` | The listings include the packaged skills, ontology and prompts. |
| T-002 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002` | connector ontology certification | Connector ontology certification passes. |
| T-003 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R003` | connector ontology certification | The blocked register lists `coversService` with its reason. |
