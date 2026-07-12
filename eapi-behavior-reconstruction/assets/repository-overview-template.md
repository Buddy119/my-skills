---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
analysis_mode: "automatic|targeted"
behavior_catalog: "behavior-catalog.yaml"
knowledge_manifest: "../knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction with a developer-oriented repository explanation. Use claim_ids for material conclusions; do not leave this comment. The headings below are reader prompts, not a mandatory outline: rename, reorder, merge, or omit sections with no useful supported content, and state each material Unknown once. -->

# Technical repository overview

## Repository purpose and boundary

Explain the repository's observable responsibility, what starts work here, what remains outside the repository, and which apparent purpose is inferred or unknown. Give the reader a coherent orientation rather than a list of Claims.

## Runtime and architecture context

Explain the deployment/runtime shape and the path from entry adapter to orchestration, data, and external boundaries. Include a small Mermaid diagram when it improves understanding.

## Main execution paths

Introduce the important Behaviors as a readable index. For each, state why a developer would open it, then link its Tech view and BA view when one exists.

## Data and external boundaries

Summarize the main information journeys, supported state-changing points, external dependencies, and outbound interactions. Link the canonical data, field, mapping, and dependency views for detail.

## Cross-cutting behavior

Explain shared validation, authorization, configuration, error handling, retry, or other reusable behavior only when it affects multiple paths.

## Reliability and change considerations

Explain important failure boundaries, opaque dependencies, partial-success risks, and code/configuration hotspots likely to matter during change analysis.

## Coverage and limitations

Explain excluded, duplicate, dynamic, unreadable, and environment-owned areas. Link the full coverage report; do not call coverage complete unless every executable entry point has a disposition.

## Where to go next

Provide role-based links to the endpoint matrix, Behaviors, API contracts, data lifecycle, field rules/mappings, runtime configuration, dependencies, failure taxonomy, BA overview, canonical manifest, and coverage report.
