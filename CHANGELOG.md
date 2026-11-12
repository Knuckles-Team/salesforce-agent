# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.8] - 2026-11-12

### Removed
- The five action-routed tools (`salesforce_soql`, `salesforce_records`, `salesforce_describe`, `salesforce_bulk`, `salesforce_admin`) and the `salesforce_input_models` module that mirrored their `params_json` payloads. Each action is already a typed per-operation tool (`salesforce_soql_query`, `salesforce_records_create`, `salesforce_describe_sobject`, `salesforce_bulk_create_ingest_job`, `salesforce_admin_user_info`, ...), so callers switch to the typed name and pass typed arguments.

### Changed
- `salesforce_ingest_crm` takes typed `sobjects` and `max_records` arguments instead of `params_json`.
- Connector surface: tool-use contracts, links, data locations, business roles, an operator prompt and two business-role prompts, ontology classes rooted in core classes, skills rewritten for the typed tools, scion-sdk 0.9.

## [2.3.7] - 2026-10-30

### Changed
- Require `scion-sdk>=0.6.4,<0.7.0`; `uv.lock` relocked.

## [2.3.5] - 2026-10-26

### Changed
- Added the canonical spec-delivery Pages dashboard and rapid-delivery development skill.

## [2.3.4] - 2026-10-24

### Changed
- Central connector migration: requires `agent-connector-sdk>=0.5.4`; server bootstrap, version, containers, ontology artifacts, security scaffold and pre-commit config are provided centrally.

## [Unreleased]
### Added
- Golden-parity standardization (gitlab-api standard): full pre-commit hook
  set (mypy/vulture/bandit/codespell/hadolint/compose checks/repo validators),
  validation scripts (`security_sanitizer`, `verify_api_integration`,
  `validate_a2a_agent`, `validate_agent`), docker quartet
  (`debug.Dockerfile`, `agent.compose.yml`, `starship.toml`), `opencode.json`,
  `uv.lock`, `main_agent.json`, per-domain tool toggles (`SOQLTOOL`,
  `RECORDSTOOL`, `DESCRIBETOOL`, `BULKTOOL`, `ADMINTOOL`), and a
  `docs/deployment.md` covering all transports, Compose, and Caddy/Technitium.
- Typed tool-input contracts in `salesforce_input_models.py` (exported from
  the package root) with model tests; API wrapper behavior tests.

### Changed
- `models.py` renamed to `salesforce_response_models.py` per the connector
  naming convention (`{short}_response_models.py`).
- `pyproject.toml` aligned to the golden shape (self-referencing `all` extra,
  ruff/mypy py310 targets, vulture config, `agent_data/**` package-data).

## [0.1.0] - 2026-06-11
### Added
- Owned thin httpx client for the Salesforce REST API (no `simple-salesforce`)
  with typed error-envelope mapping (`CONCEPT:SFDC-1.0`).
- OAuth2 client-credentials, refresh-token, and JWT bearer flows plus static
  access-token mode; token cache with expiry refresh and one retry on 401;
  sandbox vs production login URLs (`CONCEPT:SFDC-1.1`).
- Five action-routed MCP tools: `salesforce_soql` (query/query_all/explain/
  search), `salesforce_records` (CRUD, upsert by external id, composite ≤25,
  collections ≤200), `salesforce_describe` (global/sobject/record_counts/
  limits), `salesforce_bulk` (Bulk API 2.0 ingest lifecycle + capped result
  downloads), `salesforce_admin` (user/org info, list/run reports)
  (`CONCEPT:SFDC-1.2`, `CONCEPT:SFDC-1.4`).
- Safety gates: `SALESFORCE_ALLOW_DESTRUCTIVE` (default off) for all delete
  paths, per-call SOQL record caps, bulk result size caps, and secret
  redaction in errors/logs (`CONCEPT:SFDC-1.3`).
- FastMCP server (`salesforce-mcp`) with `/health`, A2A agent server
  (`salesforce-agent`), Docker packaging, docs site, and a fully mocked
  httpx test suite.
