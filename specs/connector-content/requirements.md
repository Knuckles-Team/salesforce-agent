# CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT — Requirements

Governing spec: [spec.md](spec.md).

Each row is one requirement. A row names the file it touches and the test that proves it. The generator sets each row's state in `status.json`.

| ID | Requirement | Acceptance |
|---|---|---|
| `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001` | **Default content.** `pyproject.toml` declares `salesforce-mcp` as the single `scion_sdk.connector` entry point. The server lists the packaged `skill://` and `ontology://` resources and the packaged prompts with no `content=` argument. Proving test: `tests/test_default_content_surfaces.py`. | `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. |
| `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002` | **Declare the Contract class and an SOQL access contract.** Subsystem: connector `salesforce-agent`. In `salesforce_agent/ontology/` declare class `Contract`. Declare one `ac:AccessContract` with `ac:accessKind` for the SOQL read of contracts. Set `ac:entity` `contract` and `ac:keyField` `Id`. The existing tool that runs the SOQL query is the `ac:operation`. The consumer is EG-SUPPLY-VOCAB-R005.6. | Test: `tests/test_access_contracts.py::test_contract_class_and_soql_contract` (L2) runs the connector ontology certification. |
