#!/usr/bin/env python3
"""Regression tests for manifest entity semantics and opaque field boundaries."""

from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from validate_knowledge_pack import (
    validate_entity_claim_types,
    validate_entity_scalar_claim_bindings,
    validate_field_entity,
    validate_behavior_catalog,
)


class ManifestSemanticTests(unittest.TestCase):
    def test_output_claim_cannot_create_failure_entity(self) -> None:
        errors = validate_entity_claim_types(
            "failures",
            "FAIL-local-400",
            [{"claim_type": "output"}],
        )
        self.assertTrue(any("entity-compatible claim type" in error for error in errors), errors)

    def test_failure_claim_can_create_failure_entity(self) -> None:
        errors = validate_entity_claim_types(
            "failures",
            "FAIL-explicit-exception",
            [{"claim_type": "failure"}],
        )
        self.assertEqual([], errors)

    def test_local_lookup_key_cannot_be_external_response_field(self) -> None:
        errors = validate_field_entity(
            "FIELD-status",
            {
                "boundary_kind": "outbound-http-response",
                "observation_kind": "local-lookup-key",
                "status": "Confirmed",
            },
            [{"claim_type": "output", "evidence": []}],
        )
        self.assertTrue(any("local-lookup-key must use boundary_kind local-lookup" in error for error in errors), errors)
        self.assertTrue(any("requires direct schema evidence" in error for error in errors), errors)

    def test_local_lookup_key_is_valid_as_local_observation(self) -> None:
        errors = validate_field_entity(
            "FIELD-status-lookup",
            {
                "boundary_kind": "local-lookup",
                "observation_kind": "local-lookup-key",
                "status": "Confirmed",
            },
            [{"claim_type": "output", "evidence": []}],
        )
        self.assertEqual([], errors)

    def test_confirmed_external_response_field_needs_direct_schema(self) -> None:
        entry = {
            "boundary_kind": "outbound-http-response",
            "observation_kind": "schema-field",
            "status": "Confirmed",
        }
        no_schema = validate_field_entity(
            "FIELD-external-status",
            entry,
            [
                {
                    "claim_type": "field",
                    "evidence": [
                        {
                            "source_kind": "implementation",
                            "relation": "supports",
                            "support_level": "direct",
                        }
                    ],
                }
            ],
        )
        self.assertTrue(any("requires direct schema evidence" in error for error in no_schema), no_schema)
        with_schema = validate_field_entity(
            "FIELD-external-status",
            entry,
            [
                {
                    "claim_type": "field",
                    "evidence": [
                        {
                            "source_kind": "schema",
                            "relation": "supports",
                            "support_level": "direct",
                        }
                    ],
                }
            ],
        )
        self.assertEqual([], with_schema)

    def test_manifest_field_path_must_be_claim_bound(self) -> None:
        claims = [
            {
                "statement": "The handler reads customerId.",
                "render_terms": ["customerId"],
                "subject_ids": ["FIELD-customer-id"],
                "verification": {"tokens": ["customerId"]},
            }
        ]
        good = validate_entity_scalar_claim_bindings(
            "fields", "FIELD-customer-id", {"path": "customerId"}, claims
        )
        self.assertEqual([], good)
        bad = validate_entity_scalar_claim_bindings(
            "fields", "FIELD-customer-id", {"path": "unsupportedAccountNumber"}, claims
        )
        self.assertTrue(any("manifest path is not asserted" in error for error in bad), bad)

    def test_endpoint_method_and_route_must_be_claim_bound(self) -> None:
        claims = [
            {
                "statement": "The endpoint uses POST /customers.",
                "render_terms": ["POST", "/customers"],
                "subject_ids": ["EP-POST-customers"],
                "verification": {"tokens": ["POST", "/customers"]},
            }
        ]
        good = validate_entity_scalar_claim_bindings(
            "endpoints",
            "EP-POST-customers",
            {"method": "POST", "route": "/customers"},
            claims,
        )
        self.assertEqual([], good)
        bad = validate_entity_scalar_claim_bindings(
            "endpoints",
            "EP-POST-customers",
            {"method": "DELETE", "route": "/accounts"},
            claims,
        )
        self.assertEqual(2, len(bad), bad)

    def test_behavior_catalog_identity_and_counts_must_match_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pack = Path(temporary)
            catalog = pack / "tech-pack" / "behavior-catalog.yaml"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(
                "repository: wrong-repository\n"
                "source_commit: wrong-commit\n"
                "analysis_mode: automatic\n"
                "behaviors:\n"
                "  - behavior_id: \"repo.behavior\"\n"
                "    category: \"technical\"\n"
                "    status: \"technical\"\n"
                "    duplicate_of: null\n"
                "    claim_ids: [\"CLM-entry\"]\n"
                "    document: \"behaviors/repo.behavior.md\"\n"
                "    ba_document: null\n"
                "    tech_flow_model: \"../.work/flow-models/repo.behavior.tech-flow.json\"\n"
                "    ba_flow_model: null\n"
                "    endpoint_ids: []\n"
                "    data_asset_ids: []\n"
                "    field_ids: []\n"
                "    dependency_ids: []\n"
                "    config_ids: []\n"
                "    failure_ids: []\n"
                "summary:\n"
                "  total_inventory: 99\n"
                "  pending: 0\n"
                "  documented: 0\n"
                "  technical: 1\n"
                "  duplicate: 0\n"
                "  excluded: 0\n"
                "  blocked: 0\n",
                encoding="utf-8",
            )
            behaviors = [
                {
                    "behavior_id": "repo.behavior",
                    "category": "technical",
                    "status": "technical",
                    "duplicate_of": None,
                    "claim_ids": ["CLM-entry"],
                    "document": "tech-pack/behaviors/repo.behavior.md",
                    "ba_document": None,
                    "tech_flow_model": ".work/flow-models/repo.behavior.tech-flow.json",
                    "ba_flow_model": None,
                    "endpoint_ids": [],
                    "data_asset_ids": [],
                    "field_ids": [],
                    "dependency_ids": [],
                    "config_ids": [],
                    "failure_ids": [],
                }
            ]
            errors = validate_behavior_catalog(
                catalog, pack, behaviors, "repo", "commit-1", "automatic"
            )
            joined = "\n".join(errors)
            self.assertIn("repository does not match", joined)
            self.assertIn("source_commit does not match", joined)
            self.assertIn("summary.total_inventory", joined)


if __name__ == "__main__":
    unittest.main()
