# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
