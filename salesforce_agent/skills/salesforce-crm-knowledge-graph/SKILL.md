---
name: salesforce-crm-knowledge-graph
skill_type: skill
description: >-
  Ingest Salesforce CRM accounts, contacts, opportunities and leads into the medulla knowledge graph as typed OWL nodes via the salesforce-agent MCP server. Use to mirror CRM state for cross-source reasoning or semantic search. Not for live CRUD (salesforce-record-management) or ad-hoc reads (salesforce-soql-query).
license: MIT
tags: [salesforce, crm, knowledge-graph, ingestion, mcp]
metadata:
  author: Knuckles-Team
  version: '0.1.0'
---
# Salesforce CRM → Knowledge Graph

Scope: Natively ingest Salesforce CRM objects into the medulla knowledge graph as typed OWL nodes over the salesforce-agent MCP server — accounts, contacts, opportunities, and leads become :Account/:Contact/:Opportunity/:Lead nodes (with OwnerId as a shared :Person) linked by :worksAtAccount / :opportunityForAccount / :convertedToAccount / :ownedBy. Use when the agent must mirror CRM state into the KG for cross-source reasoning or semantic search. Do NOT use for live CRUD (use salesforce-record-management) or ad-hoc reads (use salesforce-soql-query).

Push Salesforce CRM data into the ONE medulla knowledge graph as **typed OWL
nodes** matching `salesforce_agent/ontology/salesforce.ttl`. The tool runs a bounded
per-sObject SOQL SELECT and maps each record to a typed node with provenance
(`source=salesforce-agent`, `domain=salesforce`) and its relationships, via the fast
engine client. It is best-effort: with no reachable engine it no-ops (`ingested: null`).

## When to use
- Mirror accounts/contacts/opportunities/leads into the KG for cross-source reasoning
  (e.g. join CRM accounts to ITSM/EA/finance data).
- Refresh the graph after a sync so semantic search sees current CRM state.

## When NOT to use
- Live record CRUD or batching writes → `salesforce-record-management`.
- Ad-hoc reads/aggregation you don't want persisted → `salesforce-soql-query`.
- Modeling new object types — extend the ontology `.ttl` first, then map here.

## Prerequisites & environment
Connect via the `mcp-client` skill against the **`salesforce-agent`** MCP server (same
OAuth2 connected-app env as the other skills). A reachable medulla engine is
optional: the tool degrades to a no-op when none is present, so it is safe to call
without KG infrastructure.

## Steps

1. Confirm the source objects have data by calling `salesforce_soql_query` with a `SELECT Id FROM Account LIMIT 1` style probe. Verify at least one record returns.
2. Run the ingest by calling `salesforce_ingest_crm` with `sobjects` (start with `Account`) and `max_records`. Verify the response includes an `ingested` value.
3. Ingest dependent objects by calling `salesforce_ingest_crm` with `sobjects` of `Contact`, `Opportunity` and `Lead`. Verify `ingested` reports node and edge counts.
4. Confirm the nodes landed by querying the graph for `salesforce:Account:<Id>` of a known record. Verify the node exists with its `:ownedBy` link.

## Failure recovery

| Failure | Cause | Recovery |
|---------|-------|----------|
| `ingested: null` | No reachable medulla engine, so the tool no-opped | Restore the engine connection and call `salesforce_ingest_crm` again |
| Contact or Opportunity has dangling parent | Account was not ingested first | Call `salesforce_ingest_crm` with `sobjects` = `["Account"]` first, then the dependent objects |
| Authentication error | OAuth2 connected-app variables missing | Set the Salesforce connected-app variables and re-run the step 1 probe |

## Tools
| Tool | Purpose |
|------|---------|
| `salesforce_ingest_crm` | List core CRM objects via SOQL and push them into the KG as typed nodes |

### Key parameters
- `sobjects` — subset of `["Account","Contact","Opportunity","Lead"]` (default: all).
- `max_records` — per-object record cap.

## Recipes
Ingest everything: call `salesforce_ingest_crm` with no arguments.

Ingest only the sales pipeline, capped: `sobjects` = `["Account","Opportunity"]`, `max_records` = 500.

## Node & link model
| sObject | Node type | Node id | Links |
|---------|-----------|---------|-------|
| Account | `:Account` | `salesforce:Account:<Id>` | `:ownedBy` → `:Person` |
| Contact | `:Contact` | `salesforce:Contact:<Id>` | `:worksAtAccount` → `:Account`, `:ownedBy` |
| Opportunity | `:Opportunity` | `salesforce:Opportunity:<Id>` | `:opportunityForAccount` → `:Account`, `:ownedBy` |
| Lead | `:Lead` | `salesforce:Lead:<Id>` | `:convertedToAccount`/`:convertedToOpportunity`, `:ownedBy` |

## Gotchas
- Best-effort by design: `ingested: null` means no engine was reachable, not a failure.
- OwnerId is mapped onto the **shared** `:Person` class (never a Salesforce-specific
  user class) so ownership joins across sources.
- Node `type` values must stay in lock-step with `salesforce.ttl`; add a class there
  before mapping a new sObject.
- Relationship targets are minted by id even if that record wasn't in this batch — run
  Account before Contact/Opportunity to fully resolve the parent nodes.

## Related
- `salesforce-soql-query` — the read path this tool builds on.
- `salesforce-record-management` — the write path; ingest after a sync to refresh.
