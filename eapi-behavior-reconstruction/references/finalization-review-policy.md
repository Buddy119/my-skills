# Finalization three-pass review policy

## Purpose

Mechanical validation, semantic fact review, and reader review are separate trust claims. Zero Validator errors proves only the mechanical claim. Do not mark documentation quality complete until all three reviews are recorded against the same final Candidate content.

## Ownership

- The executor validates record shape, identities, paths, line ranges, coverage declarations, correction diffs, hashes, and lifecycle state.
- AI chooses representative samples, checks meaning against evidence, judges reader value, and writes corrections.
- A Review record is operational evidence of work performed. It is not a new source of repository facts and never appears in Tech or BA Reader Packs.

## Review input

Create one JSON input per Review with:

- `overall_conclusion`: `passed`, `passed-with-corrections`, or `blocked`.
- `summary`: the overall check conclusion.
- `coverage`: every category from `assets/finalization-review-schema.json`, marked `reviewed` or `not-applicable`; the latter requires a repository-specific reason.
- `items`: one or more samples for every reviewed category.
- `warning_dispositions`: every displayed Mechanical Validator warning, with the decision and reason.

Each sample contains:

- A stable `sample_id`, category, Candidate subject path, and optional identity.
- The question checked and the review conclusion.
- `passed`, `corrected`, `unresolved`, or `not-applicable` outcome.
- Findings and corrections. A corrected result names a Candidate path changed during Finalization and explains the correction.
- Semantic Fact samples cite repository source/config/Schema/test evidence with valid line ranges.

Do not mark a category `not-applicable` merely to reduce review work. Use the applicability guidance in the Editorial Policy and the presence of API, HTTP, Dependency, Failure, Java, and BA artifacts.

## Execution sequence

1. Run the complete mechanical Validator and inspect every warning.
2. Perform the Semantic Fact samples and correct unsupported or overstated conclusions.
3. Perform the Reader samples and correct unclear, repetitive, stale, or misleading publication.
4. Stabilize the Candidate. Review any sample whose subject changed during another pass.
5. Record all three Reviews against the final content:

```bash
python3 <skill-root>/scripts/stage_executor.py record-review \
  --output <output-dir> \
  --transaction <transaction-id> \
  --review mechanical|semantic-fact|reader \
  --input <review-input.json> \
  --json
```

6. Complete `mechanical-review`, `fact-sampling`, and `readability-review` Checkpoints in order.
7. Run `stage_executor.py validate`. If any Review is missing, stale, invalid, or blocked, revise or re-record it.
8. Complete `release-readiness` only after the report shows Mechanical `passed`, Semantic Fact `current`, Reader `current`, zero unresolved findings, current Reader Projections, zero Primary Errors, and zero necessary Skipped Groups.

Checkpoint completion is not a substitute for a Review record. Changing any Candidate knowledge Artifact after recording a Review makes all three records stale because they must describe one coherent final Generation.

## Mechanical Pass

Run the full structure, Artifact, Manifest, Markdown, domain, link, Fragment, citation, Projection, and publication-maturity checks. Record the Validator scope, results, warning adjudications, and mechanical corrections. Retaining a warning requires an explicit domain reason.

## Semantic Fact Review

Use the risk categories in the Review Schema. Sample the highest-impact available instance in each applicable category, not the easiest instance. For lifecycle, sample one Object State definition, one Transition and its change point, one action that correctly has no State effect, and a Derived State when present. For `evidence-qualification-projection`, sample working facts with non-Confirmed states and verify that the Reader neither drops nor upgrades their exceptional qualifiers. Confirm that cited code proves the documented meaning, state outcome, boundary relation, configuration effect, failure handling, binding, or business trace—not merely that a file or symbol exists.

For the developer implementation categories, independently sample a Behavior
Flow decision/result and an Implementation Sequence participant/order chain.
Verify the two models are not sourced from one generic flow record. Trace one
material exception from origin through handler/translation to visible and state
results. For Java, verify exact symbols plus DI/runtime binding; for
configuration, verify the read/wiring, executable effect, Behavior relation,
Endpoint relation, and caller/state/failure impact.

An unresolved semantic finding blocks publication. Preserve `Unknown` or `Conflicting` when the repository cannot support a stronger conclusion.

## Reader Review

Read without source code first. Sample the applicable overview, behavior, contract, mapping, dependency, failure, typed lifecycle, BA, navigation, and diagram surfaces. For `status-and-evidence-density`, verify that repeated Confirmed labels and per-row Evidence do not dominate the Reader view, while exceptional qualifiers and grouped Tech Source Notes remain easy to find. Confirm that readers can separately answer “what condition is the Object in?”, “what did the repository do?”, and “where did the data move?”. Record whether the intended reader can reach deeper detail without encountering repetition, audit-ledger prose, stale lifecycle wording, or misleading diagrams.

For `five-minute-repository-orientation`, `capability-main-path`, `variant-priority-and-differences`, and `high-risk-visibility`, review the Overview before opening Technical Reference. Confirm that a developer can state the repository responsibility, retell each principal Capability path, distinguish proven behavior-changing Variants without an invented default, and identify the highest-attention risks and their deep links.

For `schema-progressive-disclosure`, sample a large API Schema when available and verify that caller-required, conditional, and behaviorally significant fields precede the remaining field reference, field identities are not repeated, Schema-only basis remains clear, and a simple Contract does not contain an unnecessary completeness appendix.

Also confirm that the dual diagrams have distinct Reader value, the sequence is
legible rather than a complete call graph, API Contracts link directly to the
sequence without copying it, exception paths are discoverable, and Endpoint
navigation reaches the Java implementation slice and Config reverse-impact
index when applicable.

An unresolved reader problem blocks publication even when every link and table is mechanically valid.

## Persistence and recovery

The transaction ledger is persisted after successful Finalization under `.work/execution/reviews/`. The Finalization Receipt records its relative path, SHA-256, Candidate content hash, three statuses, and counts. The review sidecar is operational and excluded from the Knowledge Artifact Manifest.

A completed Pack without the current Review validation version requires transactional Finalization revalidation, not Artifact Migration. A current Receipt whose sidecar is missing, altered, or inconsistent is an integrity error; do not silently recreate its historical review claim.
