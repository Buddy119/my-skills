---
artifact_type: "business-model"
artifact_schema_version: "1"
repository: "repository-name"
source_commit: "git-commit-or-unknown"
business_model_status: "pending|complete|partial|blocked"
coverage_status: "complete|partial|blocked"
---

# Business model

This is the working business synthesis created after repository and Tech synthesis. Reconstruct business meaning across Behaviors; do not translate the Tech catalog row by row.

## Observable business boundary

Explain the repository-observable business responsibility and the upstream or downstream parts that remain outside the repository.

## Business capabilities

| Capability | Observable purpose and outcome | Actors or participants | Supporting Tech knowledge | Status and limitations |
|---|---|---|---|---|
| Business capability | Purpose and visible result | Business participants | Tech Behavior, Contract, Lifecycle, Dependency, or Failure references | Confirmed/Inferred/Conflicting/Unknown |

## Actors and participants

| Actor or participant | Business role | Journeys and Scenarios | Status and limitations |
|---|---|---|---|
| Person, channel, team, or business-visible system | Initiates, decides, receives, or supports an outcome | Business IDs | Confirmed/Inferred/Conflicting/Unknown |

## Business objects and lifecycle

Describe important business objects, meaningful states, ownership or responsibility changes, and unresolved lifecycle boundaries. Link the Tech lifecycle rather than copying storage operations.

## Journey records

Use semantic IDs derived from supported business goals, not Tech Behavior IDs.

| Journey ID | Business goal | Actors | Start and end conditions | Scenario IDs and order | Business-object progression | Supporting Tech Behaviors | Status and unknown boundaries |
|---|---|---|---|---|---|---|---|
| repository.journey.business-goal | Observable goal | Actors | Supported start/end or Unknown | Scenario IDs | Meaningful object changes | Behavior IDs | Confirmed/Inferred/Conflicting/Unknown |

## Scenario records

Create Scenarios from business context, decisions, and outcomes. Do not create one row per Entry Point or Tech Behavior.

| Scenario ID | Business context and goal | Actors and trigger | Material decisions | Visible outcomes | Journey IDs | Supporting Tech Behaviors | Status and limitations |
|---|---|---|---|---|---|---|---|
| repository.scenario.context-outcome | Supported situation | Business event/participant | Business decisions, not internal branches | Success/alternative/failure outcomes | Journey IDs | One or more Behavior IDs | Confirmed/Inferred/Conflicting/Unknown |

## Shared business rules

Record only rules whose business meaning and cross-Scenario applicability are supported. Preserve differences and overrides; do not promote technical validation into policy.

## Business-visible exceptions

Synthesize only failures, degradation, delays, incomplete results, false success, recovery constraints, or state inconsistency visible to a business participant or object.

## Journey–Scenario relationships

Explain ordering, reuse, alternative paths, and shared Scenarios. Record Unknown handoffs without inventing missing stages.

## Tech coverage and BA disposition

Account for every active Tech Behavior.

| Tech Behavior | BA disposition | Scenario IDs | Business-visible contribution or exclusion basis | Status and limitation |
|---|---|---|---|---|
| repository.behavior | scenario-support/business-visible-support/no-business-visible-role/unknown | Scenario IDs or N/A | Observable contribution, representation location, exclusion basis, or Unknown | Confirmed/Inferred/Conflicting/Unknown |

## Publication decisions

List the Journeys and Scenarios to publish, supported omissions, partial/blocked coverage, and business questions that remain outside this repository.
