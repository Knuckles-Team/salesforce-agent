# CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT — Test specification

Governing spec: [spec.md](spec.md).

| Test ID | Requirement | Proving test | Expected observation |
|---|---|---|---|
| T-001 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R003` | `tests/test_covers_service_source.py::test_covers_service_source_is_mapped` (planned) | The blocked register lists `coversService` with its reason. |
| T-002 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001` | `tests/test_default_content_surfaces.py::test_default_content_surfaces` (planned) | `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. |
| T-003 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002` | `tests/test_access_contracts.py::test_contract_class_and_soql_contract` (planned) | Test: `tests/test_access_contracts.py::test_contract_class_and_soql_contract` (L2) runs the connector ontology certification. |

## Negative and boundary cases

Each proving test above includes the refusal or error case that its row names. A vendor outage or an unauthorised call must return the SDK typed error.

## Quality and release proof

Run `uv run pytest tests` and `pre-commit run --all-files` from the repository root. A planned test is added by the code change that lands the row.
