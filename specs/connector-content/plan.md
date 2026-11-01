# CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT — Implementation plan

Governing spec: [spec.md](spec.md). Rows: [requirements.md](requirements.md).

## Summary

This plan states how `salesforce-agent` delivers the rows of `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT`. The live caller is the `salesforce-mcp` console script. The owner is the `salesforce_agent` package. The rows reuse the `scion-sdk` helpers and add no second authority. The plan changes no runtime code.

## Technical Context

- **Language/Version**: Python >=3.12, <3.15
- **Primary Dependencies**: scion-sdk[mcp]>=0.6.4,<0.7.0; fastmcp; further pins in `pyproject.toml` (scion-sdk[mcp]>=0.6.4,<0.7.0, httpx>=0.28.1)
- **Storage**: N/A, the connector keeps no store of its own
- **Testing**: pytest; each row names the proving test as `path::name`
- **Target Platform**: Linux container and stdio or streamable HTTP MCP clients
- **Project Type**: connector
- **Performance Goals**: N/A, the vendor service sets the latency
- **Constraints**: vendor calls go through the SDK governed client; no connector-local transport
- **Scale/Scope**: 3 active row(s) in this spec

## Constitution Check

- Organization constitution 1.5.0, spec-first change: pass. Every behaviour is a row of this spec with a bound or planned test.
- Repository article R-I, connector scope: pass. The rows stay inside this connector's one external system and reuse the SDK for shared capabilities.

## Project Structure

- `specs/connector-content/tasks.md` (existing)
- `salesforce_agent/kg_ingest.py` (existing)
- `pyproject.toml` (existing)
- `salesforce_agent/__init__.py` (existing)
- `salesforce_agent/mcp_server.py` (existing)
- `salesforce_agent/ontology/salesforce.ttl` (existing)
- `tests/test_covers_service_source.py` (new, planned)
- `tests/test_default_content_surfaces.py` (new, planned)
- `tests/test_access_contracts.py` (new, planned)

## Phase 0: Research

No unknowns. Every row names its code and test; the caller chain of each row was read from the code.

## Phase 1: Design

### Architecture

`pyproject.toml` declares `salesforce-mcp` as the connector identity. `create_mcp_server` resolves the packaged content of `salesforce_agent` from it.

## Phase 2: Task approach

`tasks.md` holds one task per row, producer first. Rows that depend on none run in parallel. A task is checked when its `Spec:` trailer is on the default branch.

## Complexity Tracking

None. The constitution check passed.

## Build contract

- `pre-commit run --all-files` runs ruff check, ruff format, the shared `connector-standard`, `spec`, `secrets` and `dependency-readiness` gates at the pinned shared revision.
- `uv run pytest tests` runs the proving tests; the shared complexity, duplication and KISS gates apply their org thresholds and this repository sets no local override.
- A change adds no scanner suppression and no duplicate implementation of an SDK helper.

## Production caller chain

- `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R003`: the supply-chain report in the engine reads the `coversService` link that this connector ingests; until an operator names the source field the register entry in `tasks.md` stays blocked and the report abstains `Uncovered`.
- `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R001`: `salesforce-mcp` in `pyproject.toml` runs `scion_sdk.cli:serve`, which builds the server from the `scion_sdk.connector` entry point `salesforce_agent:connector` (`salesforce_agent/__init__.py:11`); the SDK `Connector` then lists the packaged skills, ontology and prompts.
- `CONN-SALESFORCE-AGENT-CONNECTOR-CONTENT-R002`: arbora `fleet.call` reaches the existing SOQL tool of `salesforce_agent/mcp_server.py`; the ontology loader reads `salesforce_agent/ontology/` at server start (`salesforce_agent/__init__.py`).

## Cross-repo seams

None. The rows depend only on the published `scion-sdk` package, which the connector imports.
