# Claim-first reconstruction policy

## Contents

- Truth before pack completeness
- Mandatory generation order
- Atomic claim model
- Evidence entailment boundaries
- Claim audit
- Document rendering
- Generator restrictions

## Truth before pack completeness

Use this priority order throughout reconstruction:

1. Evidence truth and scope.
2. Explicit uncertainty and conflicts.
3. Claim-to-document traceability.
4. Inventory coverage.
5. Presentation completeness.

A sparse pack with explicit `Unknown` items is valid. A polished or fully populated pack containing unsupported statements is invalid. “Complete” means every discovered signal has a disposition; it never means every template row has been filled.

Templates define document shape only. The evidence index supplies search hints only. The manifest, catalogs, behavior metadata, flow models, filenames, symbols, comments, and a temporary generator are not proof of repository behavior.

The evidence index deliberately stores marker locations rather than source-line text. Open every indexed location in the repository before creating a claim.

## Mandatory generation order

For each analysis batch, perform these steps in order:

1. Open executable code, tests, schemas, configuration, and IaC ranges.
2. Capture exact evidence ranges and hashes with the immutable launcher's `show-evidence --json` command.
3. Write atomic claims to `.work/claim-ledger.json`.
4. Run the immutable launcher's `validate-claims` command before creating manifest entities or prose.
5. Re-read every cited range in a separate claim-audit pass. Record `Pass`, `Revise`, or `Reject` in `.work/claim-audit.json`.
6. Revise or remove every non-passing claim and rerun validation.
7. Derive manifest relationships and flow models only from passing claim IDs.
8. Render documents only from passing claims. Add an invisible `<!-- claims: CLM-... -->` marker to every factual paragraph, list item, table row, or non-Mermaid example block.
9. Run document claim-coverage and full-pack validation.

Never render documents directly from discovery metadata. Never create a large `meta` object and treat its values as established facts.

## Atomic claim model

Give every repository assertion a stable semantic ID such as `CLM-process-item-calls-save`. Do not use discovery-order numbers.

Each claim contains:

- One atomic, single-sentence statement. Split compound statements and every second sentence when different evidence proves different parts.
- Subject IDs for related behavior, endpoint, field, dependency, configuration, failure, or other manifest entities.
- Claim type, evidence status, and risk level.
- Exact evidence references, evidence kinds, support relationships, support levels, and excerpt hashes.
- Reasoning and needed evidence when the claim is not directly confirmed.

Use this exact claim shape:

```json
{
  "claim_id": "CLM-process-item-calls-save",
  "subject_ids": ["repo.process-item"],
  "claim_type": "side-effect-call",
  "statement": "The function invokes repository.save with the locally modified item.",
  "status": "Confirmed",
  "risk": "normal",
  "reasoning": null,
  "needed_evidence": null,
  "search_scope": null,
  "verification": {
    "mode": "contains-all",
    "tokens": ["repository.save"],
    "evidence_sources": ["src/handler.py:10-11"]
  },
  "render_terms": ["repository.save", "save invocation"],
  "evidence": [
    {
      "source": "src/handler.py:10-11",
      "source_kind": "implementation",
      "relation": "supports",
      "support_level": "direct",
      "excerpt_sha256": "sha256:<64 lowercase hex characters>",
      "rationale": "The selected lines call save with the modified object; they do not prove persistence success."
    }
  ]
}
```

Allowed `claim_type` values are `behavior-trigger`, `behavior-step`, `behavior-branch`, `input`, `output`, `side-effect-call`, `endpoint-contract`, `field`, `validation`, `data-read`, `data-write`, `state-transition`, `configuration`, `dependency`, `failure`, `retry`, `mapping`, `business-meaning`, `business-rule`, `business-outcome`, `coverage-gap`, `absence`, and `other`.

Every nonempty `subject_ids` value must be a real manifest entity ID. Use an empty list only for repository-wide coverage or scoped absence claims; do not invent BA-only or document-only subject IDs.

Allowed evidence `source_kind` values are `implementation`, `test`, `schema`, `configuration`, `iac`, `comment`, and `naming`. Use `relation: supports|contradicts|context` and `support_level: direct|indirect|context`.

Status rules:

- `Confirmed`: at least one direct supporting range proves the whole statement.
- `Inferred`: evidence supports a reasonable interpretation but not the whole statement directly; record reasoning and what would confirm it.
- `Conflicting`: include both supporting and contradicting ranges, then explain the unresolved conflict.
- `Unknown`: state the unanswered question or missing fact, why it cannot be established, and the evidence needed. Do not disguise an affirmative assertion as `Unknown`.

Keep explanation out of the statement and in `reasoning`. The validator rejects Unknown statements containing conjunction/list signals and rejects other statements with multiple compound signals; split method, route, trigger, actor, purpose, outcome, timeout, retry, and failure semantics into separate claims.

An `absence` claim also requires `search_scope`, listing what was actually inspected. Phrase it as “None observed within the indexed repository scope,” never as universal nonexistence.

Use `verification.mode: contains-all|contains-any` for structured claims whose method, route, field, configuration key, state literal, call, mapping, or status token must be present in supporting excerpts. Use `manual` only for narrative claims that cannot be checked lexically; structured contract claims may not opt out of machine checks.

For Confirmed or Inferred technical claims, verification tokens must appear both in the claim statement and in the cited supporting evidence. Do not choose a generic token merely because it is easy to find. `behavior-trigger`, `behavior-step`, `behavior-branch`, `input`, `output`, `dependency`, and `failure` are structured technical types too; they may not use `manual` unless the status is `Unknown`. `claim_type: other` is reserved for Unknown gaps.

Set `render_terms` to one or more short literals that must occur in every document block bound to the claim. Include supported business-language or translated terms when BA prose uses another language. These terms make a valid but unrelated claim marker fail document validation; they do not replace semantic review.

High-risk confirmed claims about authorization, monetary behavior, state persistence, transactionality, idempotency, retry/DLQ, concurrency, consumer-visible failures, or external side effects require direct support from two distinct physical files. Relabeling one range with a second `source_kind`, or citing two ranges in one file, is not independent corroboration. Otherwise downgrade the claim or state the limitation.

A Confirmed or Inferred claim may not carry contradicting evidence. When relevant contradiction exists, use `Conflicting` and present both sides.

Always mark `state-transition`, `retry`, `business-rule`, and `business-outcome` claims as high risk.

## Evidence entailment boundaries

Describe only what the cited range proves:

- A call to an opaque repository method proves that the call is attempted with observed arguments. It does not prove persistence, transaction commit, consistency, or remote state change.
- A call to an opaque messaging client proves invocation and payload construction. It does not prove delivery, publication, receipt, retry, or downstream processing.
- An in-memory assignment proves local mutation. It does not prove a persisted or business state transition unless visible persistence semantics support that conclusion.
- Indexing `request["id"]` proves indexed access. Without the runtime type or an executed test, it does not prove the exact missing-field exception.
- A `.get(...)` call proves optional lookup behavior only for a mapping-like object; do not claim a returned default for an untyped opaque input without supporting type/runtime evidence.
- A name such as `customer`, `save`, `publish`, or `DONE` may support an inference. It does not by itself establish business intent, ownership, or outcome.
- A configuration field inside a payload is not proof of AWS retry configuration.
- Absence from inspected files is `None observed within scope`, not proof that behavior does not exist elsewhere.

When a sentence contains both an observed call and an assumed outcome, split it. Confirm the call and mark the outcome `Unknown` or `Inferred` as appropriate.

## Claim audit

Perform claim audit after the ledger is drafted and before document rendering. Do not copy the claim status into the audit without re-reading evidence.

When independent subagents are available, give a fresh reviewer only the repository, claim ledger, and exact evidence ranges—not the planned pack prose—and use its verdicts to revise the ledger. Otherwise perform a clearly separate review pass before any document drafting. The authoring pass may not auto-fill `Pass`; `prepare_claim_audit.py` deliberately emits `ReviewRequired`.

For each claim, answer:

- Does the cited range support every noun, verb, qualifier, ordering statement, and outcome?
- Does the claim cross an opaque boundary?
- Does it confuse a local mutation or attempted call with an external side effect?
- Does it add business purpose from a name or template?
- Is the status too strong?
- Is contradicting evidence present elsewhere in the repository?

Record the authoring context and a different reviewer context in the audit artifact. Use `review.mode: independent-subagent` when a fresh agent performs review, or `separate-context` for a deliberately separate review pass. These identifiers improve accountability but are not cryptographic proof of independence; the workflow must still keep authoring and review separate.

Record a concise entailment explanation and an overstatement check. Only `Pass` claims may enter final documents. Validator success checks provenance integrity and coverage; it cannot replace this semantic review.

Use this top-level review metadata and exact per-claim audit shape:

```json
{
  "review": {
    "mode": "independent-subagent",
    "author_id": "author-context-id",
    "reviewer_id": "different-reviewer-context-id"
  },
  "audits": [
    {
      "claim_id": "CLM-process-item-calls-save",
      "verdict": "Pass",
      "reviewed_statement_sha256": "sha256:<hash of the exact claim statement>",
      "reviewed_claim_sha256": "sha256:<hash of the full canonical claim object>",
      "reviewed_evidence_hashes": ["sha256:<hash copied from every evidence entry>"],
      "entailment_notes": "The evidence proves invocation and argument only; the statement makes no persistence claim.",
      "overstatement_check": "Pass"
    }
  ]
}
```

## Document rendering

List all claims used by a claim-bearing Markdown document in frontmatter under `claim_ids`. Mark each factual block with the same IDs:

```markdown
The handler invokes the repository save method after assigning `DONE`. <!-- claims: CLM-process-item-assigns-done CLM-process-item-calls-save -->
```

For a Markdown table, place the marker in the final cell of each data row. Place a marker immediately before or after every code, JSON example, or Mermaid fence. Behavior Mermaid facts must additionally be traced through `summary_claim_ids` and each node's `claim_ids` in the separate flow model.

One row marker does not license unrelated cells. In the Field Catalog, type/format, requiredness, nullability, ownership/business meaning, default/source, and sensitivity values must be asserted by the bound claims. Use `Unknown` or `—` when the repository does not establish a cell; never fill it with a conventional schema assumption.

Keep each prose paragraph or list item to one auditable factual sentence. Split multiple factual sentences and bind each separately. A dynamic heading that is not a template-owned navigation heading is also a factual block and requires Claim IDs. Both `knowledge-map.md` and `coverage-report.md` are claim-bearing. Inventory counts and coverage conclusions must bind to the entity, absence, or coverage-gap Claims that justify them; deterministic counting alone cannot justify a behavioral note.

Every flow-model edge must carry nonempty `claim_ids` proving its ordering, branch, dependency, or causal relationship. Node claims do not automatically prove an edge. Never draw an edge supported only by Unknown claims; leave the nodes disconnected or use one Unknown node.

Navigation-only links, template-owned structural headings, and structural frontmatter do not require claim markers. Dynamic factual headings do. Do not use markers to launder unsupported prose: the marked text must remain within the scope of the referenced atomic claims.

## Generator restrictions

If temporary generation code such as `generate_pack_documents.py` is created:

- Accept the validated claim ledger and passing claim audit as the only factual inputs.
- Treat manifest/entity metadata as identifiers and relationships only.
- Require explicit claim IDs for every rendered factual block.
- Reject unknown claim IDs, non-passing claims, missing block markers, and template sentinel text.
- Never invent values to make a table or section look complete.
- Never turn a template example, evidence-index marker, filename, or metadata field into prose.
- Emit `Unknown` or omit a non-required row when no passing claim supports it.

Delete or keep temporary generator code only as work material; it is not repository evidence.
