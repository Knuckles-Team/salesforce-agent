# Salesforce Crm Knowledge Graph

Natively ingest Salesforce CRM objects into the epistemic-graph knowledge graph as typed OWL nodes over the salesforce-agent MCP server — accounts, contacts, opportunities, and leads become :Account/:Contact/:Opportunity/:Lead nodes (with OwnerId as a shared :Person) linked by :worksAtAccount / :opportunityForAccount / :convertedToAccount / :ownedBy. Use when the agent must mirror CRM state into the KG for cross-source reasoning or semantic search. Do NOT use for live CRUD (use salesforce-record-management) or ad-hoc reads (use salesforce-soql-query).

# Salesforce CRM → Knowledge Graph

Push Salesforce CRM data into the ONE epistemic-graph knowledge graph as **typed OWL
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
OAuth2 connected-app env as the other skills). A reachable epistemic-graph engine is
optional: the tool degrades to a no-op when none is present, so it is safe to call
without KG infrastructure.

## Tools & actions
| Condensed tool | Purpose |
|----------------|---------|
| `salesforce_ingest_crm` | List core CRM objects via SOQL and push them into the KG as typed nodes |

### Key parameters (`params_json` — a JSON **string**)
- `sobjects` — subset of `["Account","Contact","Opportunity","Lead"]` (default: all).
- `max_records` — per-object record cap.

## Recipes (`params_json`)
Ingest everything (all four core objects):
```json
{}
```
Ingest only the sales pipeline, capped:
```json
{"sobjects":["Account","Opportunity"],"max_records":500}
```

## Node & link model
| sObject | Node type | Node id | Links |
|---------|-----------|---------|-------|
| Account | `:Account` | `salesforce:Account:<Id>` | `:ownedBy` → `:Person` |
| Contact | `:Contact` | `salesforce:Contact:<Id>` | `:worksAtAccount` → `:Account`, `:ownedBy` |
| Opportunity | `:Opportunity` | `salesforce:Opportunity:<Id>` | `:opportunityForAccount` → `:Account`, `:ownedBy` |
| Lead | `:Lead` | `salesforce:Lead:<Id>` | `:convertedToAccount`/`:convertedToOpportunity`, `:ownedBy` |

## Gotchas
- `params_json` is a **string** of JSON — serialize it.
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
