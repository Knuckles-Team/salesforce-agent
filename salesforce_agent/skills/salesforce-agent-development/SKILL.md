---
name: salesforce-agent-development
skill_type: skill
domain: development
description: >-
  Develop, test, gate, and release the salesforce-agent connector. Use this
  skill when changing Salesforce API mappings, MCP tools, packaging,
  documentation, or repository gates.
license: MIT
tags: [salesforce-agent, development, connector, test, gates]
tier: repository
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---

# salesforce-agent development

This repository owns the Salesforce REST, SOQL, Bulk API, MCP, and optional A2A
surfaces. Shared connector transports and contracts belong to
`scion-sdk`; admission and serving belong to their owning
repositories. Read `AGENTS.md` before changing code and keep credentials,
endpoints, and customer data out of source, logs, and skill content.

## Rapid delivery: the 5-minute contract

Specs are already designed. Deliver small, reviewable slices and cite the
owning spec row in the commit trailer.

- Find the owning row first with `git grep -n "<term>" -- specs` and extend the
  existing spec before adding new requirement text.
- Reuse the existing SDK client, auth policy, and action-routed tool modules;
  do not add a second Salesforce transport or route implementation.
- Keep changes scoped to this connector. Work owned by the SDK, Arbora, or the
  knowledge graph belongs in that repository instead.
- Bind delivered behavior to a focused test. Generated `status.json` files are
  produced by `pipelines-hook spec-status`; never hand-edit them.
- Put `Spec: <ID>` and the assisting agent trailer on consecutive final commit
  message lines when a change delivers a requirement.

## Setup and gates

Use the pinned environment from `uv sync --locked`, then run the shared gate
from the checkout root:

```bash
uv sync --locked
uvx pre-commit run --all-files
```

For focused feedback, use the repository's actual mocked tests:

```bash
uv run --all-extras pytest tests/test_salesforce_mcp_validation.py -q
uv run --all-extras pytest tests/test_fleet_name.py tests/test_startup.py -q
```

The canonical `.pre-commit-config.yaml` delegates connector-standard, secrets,
spec, tests-fast, and dependency-readiness checks to
`Knuckles-Team/pipelines` at `rev: main`. Keep those shared hooks intact and
fix failures at their source instead of bypassing them.

## Connector-specific checks

- Mock Salesforce requests with the existing `FakeSalesforce` transport; never
  use live org credentials in local gates.
- Keep destructive record, collection, and Bulk API paths behind
  `SALESFORCE_ALLOW_DESTRUCTIVE` and enforce that policy in the API layer.
- Cite the Salesforce documentation URL in every API method docstring.
- Keep `salesforce_agent/skills/` package data intact when adding skills.
- Documentation lives under `docs/` and the generated delivery status comes
  from `specs/*/status.json`.

## Delivery discipline

Work in a real Git worktree based on `origin/main`. Inspect the complete diff,
stage only reviewed paths, and verify `git status --short` after every gate. Do
not use `git stash`, `git add -A`, or `git add .`; do not claim Pages publication
until a successful exact-source workflow run and the public dashboard are both
observed.
