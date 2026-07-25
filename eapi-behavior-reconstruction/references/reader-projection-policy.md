# Reader Projection Policy

## Purpose

Reader artifacts created in an earlier stage must represent the complete current Generation after later Endpoint, Contract, Journey, or Scenario artifacts are materialized. Treat these navigation fields and summaries as derived Reader Projections, not as new evidence or a second source of repository facts.

Use this flow in API Contract Publication, BA Publication, and Finalization revalidation:

```text
materialize downstream artifacts
→ refresh-projections
→ revise semantic projection items
→ mark-projection
→ stage validate
→ commit
```

## Ownership

The executor may only:

- invert already-authored relationships into stable backlinks;
- update Endpoint, Contract, Journey, Scenario, and Behavior IDs and paths;
- update link-only Reader sections and deterministic table cells;
- update Endpoint counts derived from the current Endpoint Matrix;
- detect incomplete indexes, stale summaries, relationship conflicts, and changed target hashes.

AI must:

- decide Endpoint, Behavior, Journey, Scenario, Dependency, Failure, and business identities;
- write or revise purpose, actors, outcomes, limitations, business meaning, and caller-visible implications;
- review every semantic Projection item;
- use `reviewed-no-change` only when the existing prose remains accurate after downstream materialization.

The executor must not create explanatory prose, invent missing table rows, select between conflicting identities, or silently repair semantic relationships.

## Projection surfaces

API materialization affects:

- Tech Behavior `api_contracts` and its visible Contract links;
- each API Contract's direct link to the related Behavior
  `#implementation-sequence`;
- Tech Behavior Catalog Contract lists;
- Endpoint Matrix Contract relationships;
- Java Implementation Map Endpoint/Behavior navigation when applicable;
- Runtime Config Matrix Endpoint reverse-impact navigation when applicable;
- Repository Overview Endpoint counts, Behavior Contract navigation, availability, and connection interpretation;
- the Field Pack API Contract Index when the Field Pack exists;
- caller-visible Failure summaries when an affected Behavior participates in a Failure Pattern.

BA materialization affects:

- Tech Behavior `ba_scenarios` and its visible Scenario links;
- Tech Behavior Catalog Scenario lists;
- Journey-derived supporting Tech Behavior links;
- Repository Overview Behavior Scenario navigation;
- BA Overview Journey Landscape;
- BA Catalog Journey, Scenario, and Tech Coverage indexes.

Do not copy complete Contracts, Scenarios, or Journeys into an upstream summary. Refresh navigation and the smallest useful explanation, then link to the owning document.

The executor may maintain stable IDs, paths, and backlinks for Java
implementation and Config impact records. AI must review any statement about
which implementation is selected, how configuration changes execution, or what
the caller observes; those are semantic Projection items.

## Commands

After all downstream artifacts for the stage have been written, run:

```bash
python3 <skill-root>/scripts/stage_executor.py refresh-projections \
  --output <output-dir> \
  --transaction <transaction-id> \
  --json
```

Read the returned transaction plan. For every `semantic_items` entry, update the Candidate document or confirm that it remains accurate. Record the result:

```bash
python3 <skill-root>/scripts/stage_executor.py mark-projection \
  --output <output-dir> \
  --transaction <transaction-id> \
  --projection <projection-id> \
  --status refreshed \
  --json
```

When no text change is justified:

```bash
python3 <skill-root>/scripts/stage_executor.py mark-projection \
  --output <output-dir> \
  --transaction <transaction-id> \
  --projection <projection-id> \
  --status reviewed-no-change \
  --reason "Existing text already reflects the materialized relationship." \
  --json
```

`refreshed` requires the target file to differ from its post-mechanical baseline. `reviewed-no-change` requires an unchanged target and a non-empty reason.

## Conflict and staleness rules

- API relationships require agreement between the Tech Behavior declaration, Contract identity, and Endpoint Matrix role.
- A Contract-to-sequence relationship also requires the target Behavior to
  expose the real `#implementation-sequence` anchor.
- Java and Config Endpoint navigation must agree with `JIMPL-*` and
  `CFG-*-I*` Register relationships; the executor cannot choose among
  conflicting bindings.
- Scenario-to-Tech and Scenario-to-Journey relationships must be authored before reverse links are generated.
- An ID, path, or relationship conflict makes the Projection invalid; the executor leaves affected Reader artifacts unchanged.
- A malformed Reader table produces one structural root cause. Do not let the executor guess a replacement table.
- Changing a downstream relationship after refresh invalidates its relationship-graph hash.
- Changing a reviewed Reader target invalidates its recorded review hash.
- Rerun `refresh-projections` after either change, then repeat only the affected semantic reviews.

## Stage gates

- Tech Publication: API and BA Projections may be `deferred`; missing future targets remain Forward References.
- API Contract Publication: API must be `current`; BA may be `deferred`.
- Business Model: committed API Projection remains current; BA remains `deferred`.
- BA Publication: API and BA must be `current` or `not-applicable`.
- Finalization: every applicable domain must be `current` with no pending or stale Projection.

A completed Pack with an older Reader Projection validation version enters transactional Finalization revalidation. Do not create a Migration Plan or rebuild working evidence merely to refresh Reader Projections.
