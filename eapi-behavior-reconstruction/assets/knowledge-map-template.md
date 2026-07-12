---
repository: "repository-name"
source_commit: "git-commit-or-unknown"
claim_ids: []
knowledge_manifest: "knowledge-manifest.yaml"
coverage_status: "complete|partial|blocked"
---

<!-- SCAFFOLD_ONLY: Replace every instruction with repository-specific orientation and navigation. Use claim_ids for material conclusions; do not leave this comment. The headings below are reader prompts, not a mandatory outline: rename, reorder, merge, or omit sections with no useful supported content, and state each material Unknown once. -->

# Repository knowledge map

## Understand this repository in 60 seconds

Explain the observable responsibility, main entry style, most important output or boundary, and the single most important limitation. Keep this short and readable.

## Choose a reading path

Give a developer, BA, tester, and change analyst a short recommended route through the pack. Use links rather than repeating canonical detail.

## Core behavior landscape

Add a small Mermaid relationship map only when it makes the repository easier to understand; a single Behavior or linear repository may need only prose and links. When used, render only supported relationships and explain how the most important Behaviors, data, and external boundaries relate.

## Important unknowns and coverage boundary

Summarize only the Unknown, Conflicting, excluded, or blocked areas that materially affect understanding. Link to the [full coverage report](coverage-report.md) and [canonical manifest](knowledge-manifest.yaml).

## Knowledge pack index

Link the Tech overview, BA overview, Behavior views, endpoint contracts, data/field/config/dependency/failure references, and machine-readable catalog without adding another inventory explanation.
