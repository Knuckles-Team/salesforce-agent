# CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT — The connector serves its packaged content

Owner: salesforce-agent. Cross-repo IDs: `SCION-CONNECTOR-CONTROL-R071`, `SCION-CONNECTOR-CONTROL-R073`.

## Purpose and user stories

The `salesforce-mcp` server serves its packaged skills, prompts and ontology to any client, with no wiring of its own.

## Delivery mapping

Component: salesforce-agent connector

Code: ../../salesforce_agent/__init__.py

## User Scenarios & Testing

### User Story 1 - Record the `coversService` source (BLOCKED, owner: operator) (Priority: P1)

The fleet operator and the engine rely on this behaviour of `salesforce-agent`: Name the custom field or curated link that carries contract to service. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `salesforce-agent` connector built from the default branch, **When** `tests/test_covers_service_source.py::test_covers_service_source_is_mapped` runs, **Then** the blocked register lists `coversService` with its reason.

### User Story 2 - Default content (Priority: P1)

The fleet operator and the engine rely on this behaviour of `salesforce-agent`: `pyproject.toml` declares `salesforce-mcp` as the single `scion_sdk.connector` entry point. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `salesforce-agent` connector built from the default branch, **When** `tests/test_default_content_surfaces.py::test_default_content_surfaces` runs, **Then** `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt.

### User Story 3 - Declare the Contract class and an SOQL access contract (Priority: P1)

The fleet operator and the engine rely on this behaviour of `salesforce-agent`: Subsystem: connector `salesforce-agent`. It is proven independently of the other stories.

**Acceptance Scenarios**:

1. **Given** the `salesforce-agent` connector built from the default branch, **When** `tests/test_access_contracts.py::test_contract_class_and_soql_contract` runs, **Then** test: `tests/test_access_contracts.py::test_contract_class_and_soql_contract` (L2) runs the connector ontology certification.

### Edge Cases

- The vendor service is unreachable or rejects the credential: the connector returns the SDK typed error and never a partial result.
- An argument outside the documented inputs is refused with the SDK typed refusal and causes no effect on the vendor service.

## Requirements

- **FR-001**: Record the `coversService` source (BLOCKED, owner: operator). Rows: `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R003`.
- **FR-002**: Default content. Rows: `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001`.
- **FR-003**: Declare the Contract class and an SOQL access contract. Rows: `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002`.

## Success Criteria

- **SC-001**: The blocked register lists `coversService` with its reason. Rows: `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R003`.
- **SC-002**: `resources/list` includes `skill://` and `ontology://`; `prompts/list` includes each packaged prompt. Rows: `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001`.
- **SC-003**: Test: `tests/test_access_contracts.py::test_contract_class_and_soql_contract` (L2) runs the connector ontology certification. Rows: `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002`.

## Assumptions

- The `salesforce-agent` package keeps the entry point and module layout named in the rows.
- The shared SDK supplies the transport, authentication, retry and certification helpers the rows reuse.

## Why a new spec

Searched `specs/` of `salesforce-agent` with `git grep` for the terms of this spec. No other spec of this repository owns the capability, so this spec owns it.

## Traceability

| Label | Rows | Design section | Test ID | Evidence |
|---|---|---|---|---|
| FR-001 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R003` | plan.md Production caller chain | T-001 | tests/test_covers_service_source.py::test_covers_service_source_is_mapped |
| FR-002 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001` | plan.md Production caller chain | T-002 | tests/test_default_content_surfaces.py::test_default_content_surfaces |
| FR-003 | `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002` | plan.md Production caller chain | T-003 | tests/test_access_contracts.py::test_contract_class_and_soql_contract |
