from __future__ import annotations

import importlib.util
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = SKILL_ROOT / "scripts" / "stage_executor.py"


def raw_tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def load_executor_module():
    sys.path.insert(0, str(EXECUTOR.parent))
    specification = importlib.util.spec_from_file_location("stage_executor", EXECUTOR)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    try:
        specification.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def api_behavior_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "tech-behavior"\n'
        'artifact_schema_version: "1"\n'
        'behavior_id: "sample-repo.get-customer"\n'
        'title: "Get customer"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'entry_type: "api"\n'
        'entry_point: "GET /customers/{id}"\n'
        'behavior_category: "business"\n'
        'overall_status: "Confirmed"\n'
        "api_contracts:\n"
        '  - endpoint_id: "sample-repo.get-customer"\n'
        '    document: "../contracts/sample-repo.get-customer.api-contract.md"\n'
        "ba_scenarios: []\n"
        "consumes: []\n"
        "produces: []\n"
        "reads: []\n"
        "writes: []\n"
        "external_dependencies: []\n"
        "external_http_calls: []\n"
        "field_mappings: []\n"
        "failure_patterns: []\n"
        "analysis_limitations: []\n"
        "---\n\n"
        "# Get customer\n\n"
        "## Summary\n\nReturns the observed customer result. `src/Handler.java:1`\n\n"
        "## Trigger and entry point\n\nThe application route invokes the handler.\n\n"
        "## API contracts\n\n"
        "- [GET /customers/{id}](../contracts/sample-repo.get-customer.api-contract.md)\n\n"
        "## Behavior flow\n\n```mermaid\nflowchart TD\n    A[Request] --> B[Response]\n```\n\n"
        "## Inputs\n\nThe caller input is defined in the API Contract.\n\n"
        "## Preconditions and business rules\n\nNo additional rule was observed.\n\n"
        "## Happy path\n\n1. Accept the request.\n2. Return the result.\n\n"
        "## Data access and state changes\n\nNo state change was observed.\n\n"
        "## Outputs and side effects\n\nReturns the caller-visible response.\n\n"
        "## Failures, retries, and partial success\n\nNo retry was observed.\n\n"
        "## Open questions and conflicts\n\nExternal deployment remains Unknown.\n\n"
        "## Evidence index\n\n- `src/Handler.java:1`\n"
    )


def endpoint_matrix_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "endpoint-matrix"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'coverage_status: "complete"\n'
        "---\n\n"
        "# Endpoint matrix\n\n"
        "## Endpoint summary\n\n"
        "| Endpoint or Exposure ID | Operation Role | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| `sample-repo.get-customer` | application-endpoint | Confirmed — `GET /customers/{id}` | Not observed | Not observed | Not observed | Not observed | [Behavior](behaviors/sample-repo.get-customer.md) | [Contract](contracts/sample-repo.get-customer.api-contract.md) |\n\n"
        "## Evidence and reconciliation notes\n\n"
        '<a id="sample-repo-get-customer"></a>\n\n'
        "### `sample-repo.get-customer`\n\n"
        "| Layer | Observed value | Status | Evidence |\n"
        "|---|---|---|---|\n"
        "| Application Route | `GET /customers/{id}` | Confirmed | `src/Handler.java:1` |\n"
        "| External Entry Declaration | None observed | Not observed | Repository scope reviewed |\n"
        "| Environment Deployment Intent | None observed | Not observed | Repository scope reviewed |\n"
        "| Observed Runtime Deployment | None supplied | Not observed | Analysis boundary |\n"
        "| External Reachability Assessment | No external exposure evidence | Not observed | Derived from the preceding rows |\n\n"
        "## Unknowns and conflicts\n\nExternal deployment remains Unknown.\n"
    )


def api_contract_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "api-contract"\n'
        'artifact_schema_version: "2"\n'
        'behavior_id: "sample-repo.get-customer"\n'
        'endpoint_id: "sample-repo.get-customer"\n'
        'title: "Get customer API"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'entry_point: "GET /customers/{id}"\n'
        'method: "GET"\n'
        'route: "/customers/{id}"\n'
        'contract_status: "Confirmed"\n'
        'application_route_status: "Confirmed"\n'
        'external_reachability_status: "Not observed"\n'
        'behavior_document: "../behaviors/sample-repo.get-customer.md"\n'
        'endpoint_matrix: "../endpoint-matrix.md#sample-repo-get-customer"\n'
        "---\n\n"
        "# Get customer API\n\n"
        "Returns the observed customer result to the caller. [E1](#e1)\n\n"
        "## Quick reference\n\n"
        "| Property | Value |\n"
        "|---|---|\n"
        "| Method and application route | `GET /customers/{id}` [E1](#e1) |\n"
        "| Authentication | Unknown |\n"
        "| Content type | Unknown |\n"
        "| Contract confidence | Confirmed |\n"
        "| External reachability | [Not observed](../endpoint-matrix.md#sample-repo-get-customer) |\n\n"
        "## Request\n\nThe route contains the customer identifier; further wire rules are Unknown.\n\n"
        "## Responses\n\n"
        "| HTTP status | When | Body/schema | Relevant headers |\n"
        "|---|---|---|---|\n"
        "| 200 | The handler completes | Customer result [E1](#e1) | None observed |\n\n"
        "## Related documents\n\n"
        "- [Tech Behavior](../behaviors/sample-repo.get-customer.md)\n"
        "- [Endpoint Matrix](../endpoint-matrix.md#sample-repo-get-customer)\n\n"
        "## Source notes\n\n"
        '<a id="e1"></a> **E1** — `src/Handler.java:1` establishes the route and observed response.\n'
    )


COMPLETE_BEHAVIOR_ID = "sample-repo.manage-customer"
COMPLETE_JOURNEY_ID = "sample-repo.journey.manage-customer-profile"
COMPLETE_SCENARIO_ID = "sample-repo.scenario.customer-profile-request-completed"
COMPLETE_ENDPOINTS = (
    ("sample-repo.get-customer", "GET", "/customers/{id}", 2),
    ("sample-repo.put-customer", "PUT", "/customers/{id}", 3),
)


def complete_api_behavior_fixture(*, include_ba: bool) -> str:
    api_contracts = "api_contracts:\n" + "".join(
        f'  - endpoint_id: "{endpoint_id}"\n'
        f'    document: "../contracts/{endpoint_id}.api-contract.md"\n'
        for endpoint_id, _method, _route, _line in COMPLETE_ENDPOINTS
    )
    ba_scenarios = "ba_scenarios: []\n"
    ba_section = ""
    if include_ba:
        ba_scenarios = (
            "ba_scenarios:\n"
            f'  - scenario_id: "{COMPLETE_SCENARIO_ID}"\n'
            f'    document: "../../ba-pack/scenarios/{COMPLETE_SCENARIO_ID}.md"\n'
        )
        ba_section = (
            "## BA scenarios\n\n"
            f"- [Customer profile request completed]"
            f"(../../ba-pack/scenarios/{COMPLETE_SCENARIO_ID}.md)\n\n"
        )
    contract_links = "".join(
        f"- [{method} {route}](../contracts/{endpoint_id}.api-contract.md)\n"
        for endpoint_id, method, route, _line in COMPLETE_ENDPOINTS
    )
    return (
        "---\n"
        'artifact_type: "tech-behavior"\n'
        'artifact_schema_version: "1"\n'
        f'behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
        'title: "Manage customer profile"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'entry_type: "api"\n'
        'entry_point: "GET or PUT /customers/{id}"\n'
        'behavior_category: "business"\n'
        'overall_status: "Confirmed"\n'
        + api_contracts
        + ba_scenarios
        + "consumes: []\n"
        "produces: []\n"
        "reads: []\n"
        "writes: []\n"
        "external_dependencies: []\n"
        "external_http_calls: []\n"
        "field_mappings: []\n"
        "failure_patterns: []\n"
        "analysis_limitations: []\n"
        "---\n\n"
        "# Manage customer profile\n\n"
        "## Summary\n\nGets or updates the observed customer profile. `src/Handler.java:2-3`\n\n"
        "## Trigger and entry point\n\nThe application routes invoke the same profile behavior.\n\n"
        "## API contracts\n\n"
        + contract_links
        + "\n"
        + ba_section
        + "## Behavior flow\n\n"
        "```mermaid\nflowchart TD\n    A[Profile request] --> B{Read or update}\n"
        "    B --> C[Return profile result]\n```\n\n"
        "## Inputs\n\nCaller inputs are defined by the endpoint Contracts.\n\n"
        "## Preconditions and business rules\n\nThe route selects the requested profile operation.\n\n"
        "## Happy path\n\n1. Accept the profile request.\n2. Return the observed result.\n\n"
        "## Data access and state changes\n\nNo durable state is modeled by this fixture.\n\n"
        "## Outputs and side effects\n\nReturns the caller-visible profile result.\n\n"
        "## Failures, retries, and partial success\n\nNo retry or partial success is modeled.\n\n"
        "## Open questions and conflicts\n\nExternal deployment remains Unknown.\n\n"
        "## Evidence index\n\n- `src/Handler.java:2-3`\n"
    )


def complete_tech_catalog_fixture(*, include_ba: bool) -> str:
    ba_scenarios = "    ba_scenarios: []\n"
    if include_ba:
        ba_scenarios = (
            "    ba_scenarios:\n"
            f'      - scenario_id: "{COMPLETE_SCENARIO_ID}"\n'
            f'        document: "../ba-pack/scenarios/{COMPLETE_SCENARIO_ID}.md"\n'
        )
    api_contracts = "".join(
        f'      - endpoint_id: "{endpoint_id}"\n'
        f'        document: "contracts/{endpoint_id}.api-contract.md"\n'
        for endpoint_id, _method, _route, _line in COMPLETE_ENDPOINTS
    )
    return (
        'artifact_type: "tech-behavior-catalog"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'analysis_mode: "automatic"\n'
        "behaviors:\n"
        f'  - behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
        '    title: "Manage customer profile"\n'
        '    category: "business"\n'
        "    triggers:\n"
        '      - type: "api"\n'
        '        name: "GET or PUT /customers/{id}"\n'
        "    entry_points:\n"
        '      - "src/Handler.java:2"\n'
        '      - "src/Handler.java:3"\n'
        '    status: "documented"\n'
        "    duplicate_of: null\n"
        f'    document: "behaviors/{COMPLETE_BEHAVIOR_ID}.md"\n'
        + ba_scenarios
        + "    api_contracts:\n"
        + api_contracts
    )


def complete_endpoint_matrix_fixture() -> str:
    rows = "".join(
        f"| `{endpoint_id}` | application-endpoint | Confirmed — `{method} {route}` | "
        "Not observed | Not observed | Not observed | Not observed | "
        f"[Behavior](behaviors/{COMPLETE_BEHAVIOR_ID}.md) | "
        f"[Contract](contracts/{endpoint_id}.api-contract.md) |\n"
        for endpoint_id, method, route, _line in COMPLETE_ENDPOINTS
    )
    details = "".join(
        f'<a id="{endpoint_id.replace(".", "-")}"></a>\n\n'
        f"### `{endpoint_id}`\n\n"
        "| Layer | Observed value | Status | Evidence |\n"
        "|---|---|---|---|\n"
        f"| Application Route | `{method} {route}` | Confirmed | `src/Handler.java:{line}` |\n"
        "| External Entry Declaration | None observed | Not observed | Repository scope reviewed |\n"
        "| Environment Deployment Intent | None observed | Not observed | Repository scope reviewed |\n"
        "| Observed Runtime Deployment | None supplied | Not observed | Analysis boundary |\n"
        "| External Reachability Assessment | No exposure evidence | Not observed | Derived from the preceding rows |\n\n"
        for endpoint_id, method, route, line in COMPLETE_ENDPOINTS
    )
    return (
        "---\n"
        'artifact_type: "endpoint-matrix"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'coverage_status: "complete"\n'
        "---\n\n"
        "# Endpoint matrix\n\n"
        "## Endpoint summary\n\n"
        "| Endpoint or Exposure ID | Operation Role | Application Route | External Entry Declaration | Environment Deployment Intent | Observed Runtime Deployment | External Reachability | Behavior | Contract |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        + rows
        + "\n## Evidence and reconciliation notes\n\n"
        + details
        + "## Unknowns and conflicts\n\nExternal deployment remains Unknown.\n"
    )


def complete_api_contract_fixture(
    endpoint_id: str, method: str, route: str, source_line: int
) -> str:
    anchor = endpoint_id.replace(".", "-")
    return (
        "---\n"
        'artifact_type: "api-contract"\n'
        'artifact_schema_version: "2"\n'
        f'behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
        f'endpoint_id: "{endpoint_id}"\n'
        f'title: "{method} customer profile API"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        f'entry_point: "{method} {route}"\n'
        f'method: "{method}"\n'
        f'route: "{route}"\n'
        'contract_status: "Confirmed"\n'
        'application_route_status: "Confirmed"\n'
        'external_reachability_status: "Not observed"\n'
        f'behavior_document: "../behaviors/{COMPLETE_BEHAVIOR_ID}.md"\n'
        f'endpoint_matrix: "../endpoint-matrix.md#{anchor}"\n'
        "---\n\n"
        f"# {method} customer profile API\n\n"
        "Provides the observed profile result to the caller. [E1](#e1)\n\n"
        "## Quick reference\n\n"
        "| Property | Value |\n"
        "|---|---|\n"
        f"| Method and application route | `{method} {route}` [E1](#e1) |\n"
        "| Authentication | Unknown |\n"
        "| Content type | Unknown |\n"
        "| Contract confidence | Confirmed |\n"
        f"| External reachability | [Not observed](../endpoint-matrix.md#{anchor}) |\n\n"
        "## Request\n\nThe route contains a customer identifier; further wire rules are Unknown.\n\n"
        "## Responses\n\n"
        "| HTTP status | When | Body/schema | Relevant headers |\n"
        "|---|---|---|---|\n"
        "| 200 | The handler completes | Customer profile result [E1](#e1) | None observed |\n\n"
        "## Related documents\n\n"
        f"- [Tech Behavior](../behaviors/{COMPLETE_BEHAVIOR_ID}.md)\n"
        f"- [Endpoint Matrix](../endpoint-matrix.md#{anchor})\n\n"
        "## Source notes\n\n"
        f'<a id="e1"></a> **E1** — `src/Handler.java:{source_line}` establishes the route and response.\n'
    )


def complete_ba_scenario_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "ba-scenario"\n'
        'artifact_schema_version: "1"\n'
        f'scenario_id: "{COMPLETE_SCENARIO_ID}"\n'
        'title: "Customer profile request completed"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        "business_capabilities:\n"
        '  - "Manage customer profile"\n'
        'overall_status: "Confirmed"\n'
        "actors:\n"
        '  - "Customer channel"\n'
        "journeys:\n"
        f'  - journey_id: "{COMPLETE_JOURNEY_ID}"\n'
        f'    document: "../journeys/{COMPLETE_JOURNEY_ID}.md"\n'
        "tech_behaviors:\n"
        f'  - behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
        f'    document: "../../tech-pack/behaviors/{COMPLETE_BEHAVIOR_ID}.md"\n'
        "---\n\n"
        "# Customer profile request completed\n\n"
        "## Business purpose and context\n\nA customer channel requests a profile result.\n\n"
        "## Business flow\n\n"
        "```mermaid\nflowchart TD\n    A[Profile need] --> B[Request profile result]\n"
        "    B --> C[Receive visible outcome]\n```\n\n"
        "## Business outcomes\n\nThe channel receives the observable profile outcome.\n\n"
        "## Traceability\n\n"
        f"- [Business Journey](../journeys/{COMPLETE_JOURNEY_ID}.md)\n"
        f"- [Technical Behavior](../../tech-pack/behaviors/{COMPLETE_BEHAVIOR_ID}.md)\n"
    )


def complete_ba_journey_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "ba-journey"\n'
        'artifact_schema_version: "1"\n'
        f'journey_id: "{COMPLETE_JOURNEY_ID}"\n'
        'title: "Manage customer profile"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        "business_capabilities:\n"
        '  - "Manage customer profile"\n'
        'overall_status: "Confirmed"\n'
        "actors:\n"
        '  - "Customer channel"\n'
        "scenarios:\n"
        f'  - scenario_id: "{COMPLETE_SCENARIO_ID}"\n'
        f'    document: "../scenarios/{COMPLETE_SCENARIO_ID}.md"\n'
        "supporting_tech_behaviors:\n"
        f'  - behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
        f'    document: "../../tech-pack/behaviors/{COMPLETE_BEHAVIOR_ID}.md"\n'
        "---\n\n"
        "# Manage customer profile\n\n"
        "## Business goal and scope\n\nObtain or update the observable customer profile result.\n\n"
        "## Journey map\n\n"
        "```mermaid\nflowchart LR\n    A[Profile goal] --> B[Profile scenario]\n"
        "    B --> C[Observable result]\n```\n\n"
        "## Stages and scenarios\n\n"
        f"- [Customer profile request completed](../scenarios/{COMPLETE_SCENARIO_ID}.md)\n\n"
        "## Traceability\n\n"
        f"- [Business Scenario](../scenarios/{COMPLETE_SCENARIO_ID}.md)\n"
        f"- [Technical Behavior](../../tech-pack/behaviors/{COMPLETE_BEHAVIOR_ID}.md)\n"
    )


def complete_ba_overview_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "ba-overview"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'business_model_status: "complete"\n'
        'coverage_status: "complete"\n'
        'business_catalog: "business-catalog.md"\n'
        "---\n\n"
        "# Business overview\n\n"
        "The repository supports the observable customer profile journey.\n\n"
        "## Journey landscape\n\n"
        f"- [Manage customer profile](journeys/{COMPLETE_JOURNEY_ID}.md)\n\n"
        "## Business scenarios\n\n"
        f"- [Customer profile request completed](scenarios/{COMPLETE_SCENARIO_ID}.md)\n\n"
        "## Related technical view\n\n"
        "- [Repository overview](../tech-pack/repository-overview.md)\n"
        "- [Business catalog](business-catalog.md)\n"
    )


def complete_ba_catalog_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "ba-catalog"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'business_model_status: "complete"\n'
        'coverage_status: "complete"\n'
        "---\n\n"
        "# Business catalog\n\n"
        "## Journey index\n\n"
        f"- [Manage customer profile](journeys/{COMPLETE_JOURNEY_ID}.md)\n\n"
        "## Scenario index\n\n"
        f"- [Customer profile request completed](scenarios/{COMPLETE_SCENARIO_ID}.md)\n\n"
        "## Tech coverage map\n\n"
        f"- [Manage customer profile](../tech-pack/behaviors/{COMPLETE_BEHAVIOR_ID}.md)"
        f" supports [the business scenario](scenarios/{COMPLETE_SCENARIO_ID}.md).\n\n"
        "- [Business overview](business-overview.md)\n"
        "- [Technical catalog](../tech-pack/behavior-catalog.yaml)\n"
    )


def complete_dossier_fixture() -> str:
    return (
        "---\n"
        'artifact_type: "behavior-dossier"\n'
        'artifact_schema_version: "1"\n'
        f'behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
        'working_title: "Manage customer profile"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'understanding_status: "understood"\n'
        'entry_type: "api"\n'
        'entry_points:\n'
        '  - "src/Handler.java:2"\n'
        '  - "src/Handler.java:3"\n'
        "---\n\n"
        "# Manage customer profile working dossier\n\n"
        "## Working purpose and boundary\n\n"
        "The two application routes expose the repository-observable profile behavior.\n\n"
        "## End-to-end executable narrative\n\n"
        "The handler accepts either read or update intent and returns the profile result.\n\n"
        "## Semantic symbol and call trace\n\n"
        "Java source was inspected in degraded mode; the two exact methods are the framework boundary.\n\n"
        "## Endpoint exposure evidence\n\n"
        "Both application routes are confirmed; external deployment evidence was not supplied.\n\n"
        "## Input handling and validation\n\nThe path identifies the customer.\n\n"
        "## Decisions and rules\n\nThe HTTP method selects read or update intent.\n\n"
        "## Main successful path\n\nThe handler accepts the request and returns a profile result.\n\n"
        "## Data, business objects, and state\n\nNo durable state is modeled in this fixture.\n\n"
        "## Boundaries, outputs, and side effects\n\nTwo caller-visible application routes were observed.\n\n"
        "## Failures, retry, and partial success\n\nNo retry or partial success was observed.\n\n"
        "## Runtime configuration and IaC\n\nNo deployment configuration was supplied.\n\n"
        "## Test observations\n\nThis lifecycle fixture tests publication mechanics.\n\n"
        "## Evidence anchors\n\n- `src/Handler.java:2-3` — the application methods.\n\n"
        "## Unknowns, conflicts, and limitations\n\nExternal reachability remains unknown.\n\n"
        "## Repository register contributions\n\nEndpoint evidence and reconciliation rows were added.\n\n"
        "## Understanding gate\n\nThe observable fixture behavior is understood.\n"
    )


def complete_register_fixture(executor) -> str:
    schema = json.loads(
        (SKILL_ROOT / "assets" / "register-schema.json").read_text(encoding="utf-8")
    )
    tables = {table["section"]: table["headers"] for table in schema["tables"].values()}
    endpoint_evidence = {
        "Endpoint evidence records": [
            [
                "EP-EV-001",
                "Application Route",
                "GET /customers/{id} handled by Handler.getCustomer",
                "Application source",
                "sample-repo.get-customer",
                "Confirmed",
                "`src/Handler.java:2`",
            ],
            [
                "EP-EV-002",
                "Application Route",
                "PUT /customers/{id} handled by Handler.putCustomer",
                "Application source",
                "sample-repo.put-customer",
                "Confirmed",
                "`src/Handler.java:3`",
            ],
        ],
        "Endpoint reconciliation": [
            [
                endpoint_id,
                "application-endpoint",
                "publish",
                "customers-id",
                f"Confirmed — {method} {route}",
                "Not observed",
                "Not observed",
                "Not observed",
                "Not observed",
                COMPLETE_BEHAVIOR_ID,
                f"contracts/{endpoint_id}.api-contract.md",
                "Executable application method",
                "No external exposure evidence was supplied",
            ]
            for endpoint_id, method, route, _line in COMPLETE_ENDPOINTS
        ],
    }
    parts = [
        "---",
        'artifact_type: "repository-register"',
        'artifact_schema_version: "1"',
        'repository: "sample-repo"',
        'source_commit: "unknown"',
        'register_status: "reconciled"',
        "---",
        "",
        "# Repository register",
    ]
    for heading in sorted(executor.REGISTER_HEADINGS):
        headers = tables[heading]
        parts.extend(["", f"## {heading}", ""])
        parts.append("| " + " | ".join(headers) + " |")
        parts.append("|" + "|".join("---" for _ in headers) + "|")
        for row in endpoint_evidence.get(heading, []):
            assert len(row) == len(headers)
            parts.append("| " + " | ".join(row) + " |")
    return "\n".join(parts) + "\n"


def complete_repository_synthesis_fixture(executor) -> str:
    return (
        "---\n"
        'artifact_type: "repository-synthesis"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        "---\n\n"
        "# Repository synthesis\n\n"
        + "\n\n".join(
            f"## {heading}\n\nThe lifecycle fixture records the reconciled repository view."
            for heading in sorted(executor.SYNTHESIS_HEADINGS)
        )
        + "\n"
    )


def complete_business_model_fixture(executor) -> str:
    sections = {
        "Journey records": (
            f"`{COMPLETE_JOURNEY_ID}` organizes the observable profile goal and "
            f"contains `{COMPLETE_SCENARIO_ID}`."
        ),
        "Scenario records": (
            f"`{COMPLETE_SCENARIO_ID}` is supported by `{COMPLETE_BEHAVIOR_ID}`."
        ),
        "Tech coverage and BA disposition": (
            f"`{COMPLETE_BEHAVIOR_ID}` has disposition `scenario-support` for "
            f"`{COMPLETE_SCENARIO_ID}`."
        ),
    }
    return (
        "---\n"
        'artifact_type: "business-model"\n'
        'artifact_schema_version: "1"\n'
        'repository: "sample-repo"\n'
        'source_commit: "unknown"\n'
        'business_model_status: "complete"\n'
        'coverage_status: "complete"\n'
        "---\n\n"
        "# Business model\n\n"
        + "\n\n".join(
            f"## {heading}\n\n{sections.get(heading, 'The fixture has no additional business-model observation for this section.')}"
            for heading in sorted(executor.BUSINESS_MODEL_HEADINGS)
        )
        + "\n"
    )


class StageExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "sample-repo"
        self.repo.mkdir()
        self.output = self.root / "knowledge"
        self.run_cmd("init", "--repo", str(self.repo), "--output", str(self.output))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cmd(self, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        if arguments and arguments[0] == "commit":
            values = list(arguments)
            output = Path(values[values.index("--output") + 1])
            transaction = values[values.index("--transaction") + 1]
            self.complete_checkpoints(transaction, output=output)
        result = subprocess.run(
            [sys.executable, str(EXECUTOR), *arguments, "--json"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            expected,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        return result

    def begin(self, stage: str) -> tuple[str, Path]:
        result = self.run_cmd("begin", "--output", str(self.output), "--stage", stage)
        payload = json.loads(result.stdout)
        return payload["transaction_id"], Path(payload["candidate"])

    def complete_checkpoints(
        self, transaction: str, *, output: Path | None = None
    ) -> None:
        output = output or self.output
        tx_dir = output / ".work" / "execution" / "transactions" / transaction
        ledger_path = tx_dir / "checkpoints.json"
        if not ledger_path.is_file():
            return
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for item in ledger["checkpoints"]:
            if item["status"] in {"complete", "skipped", "blocked"}:
                continue
            completed = subprocess.run(
                [
                    sys.executable,
                    str(EXECUTOR),
                    "checkpoint",
                    "--output",
                    str(output),
                    "--transaction",
                    transaction,
                    "--checkpoint",
                    item["checkpoint_id"],
                    "--status",
                    "complete",
                    "--json",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_partial_candidate_does_not_advance_formal_state(self) -> None:
        transaction, candidate = self.begin("inventory")
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertIn("evidence-index.json", " ".join(payload["errors"]))
        formal = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "inventory"', formal)
        self.assertIn('stage_status: "failed"', formal)
        self.assertTrue(candidate.is_dir())
        receipts = list((self.output / ".work" / "execution" / "receipts").glob("*-inventory.json"))
        self.assertEqual(receipts, [])

    def test_inventory_commit_creates_receipt_and_advances_once(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)
        status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(status["current_stage"], "tracing")
        self.assertEqual(status["stage_status"], "pending")
        self.assertIsNone(status["active_transaction"])
        receipts = list((self.output / ".work" / "execution" / "receipts").glob("*-inventory.json"))
        self.assertEqual(len(receipts), 1)
        receipt = json.loads(receipts[0].read_text(encoding="utf-8"))
        self.assertEqual(receipt["result"], "committed")
        self.assertEqual(receipt["stage"], "inventory")
        self.assertFalse(candidate.exists())

    def test_state_uses_stage_and_checkpoint_without_legacy_phase(self) -> None:
        state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertNotIn("\nphase:", "\n" + state)
        transaction, _candidate = self.begin("inventory")
        status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertEqual(status["current_stage"], "inventory")
        self.assertEqual(status["current_checkpoint"], "project-detection")
        self.assertEqual(status["checkpoint_status"], "in-progress")
        self.assertEqual(len(status["checkpoints"]), 3)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_status_distinguishes_formal_and_candidate_manifest_staleness(self) -> None:
        initialized = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(initialized["artifact_manifest_status"], "valid")
        self.assertEqual(
            initialized["candidate_artifact_manifest_status"], "not-applicable"
        )
        self.assertEqual(initialized["manifest_refresh_pending"], "none")

        transaction, candidate = self.begin("inventory")
        begun = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(begun["artifact_manifest_status"], "stale")
        self.assertEqual(begun["artifact_manifest_errors"], [])
        self.assertEqual(
            begun["artifact_manifest_stale_reasons"],
            [
                "artifact manifest checksum differs from file: "
                ".work/analysis-state.yaml"
            ],
        )
        self.assertEqual(begun["candidate_artifact_manifest_status"], "valid")
        self.assertEqual(begun["manifest_refresh_pending"], "formal")
        self.assertFalse(
            any("Artifact Schema:" in requirement for requirement in begun["requirements"])
        )

        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        formal_manifest_before_status = (
            self.output / ".work" / "artifact-manifest.json"
        ).read_bytes()
        candidate_manifest_before_status = (
            candidate / ".work" / "artifact-manifest.json"
        ).read_bytes()
        edited = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(edited["artifact_manifest_status"], "stale")
        self.assertEqual(edited["candidate_artifact_manifest_status"], "stale")
        self.assertEqual(edited["candidate_artifact_manifest_errors"], [])
        self.assertIn(
            "artifact is missing from manifest: .work/evidence-index.json",
            edited["candidate_artifact_manifest_stale_reasons"],
        )
        self.assertEqual(edited["manifest_refresh_pending"], "both")
        self.assertFalse(
            any("Artifact Schema:" in requirement for requirement in edited["requirements"])
        )
        self.assertEqual(
            (self.output / ".work" / "artifact-manifest.json").read_bytes(),
            formal_manifest_before_status,
        )
        self.assertEqual(
            (candidate / ".work" / "artifact-manifest.json").read_bytes(),
            candidate_manifest_before_status,
        )
        executor = load_executor_module()
        self.assertTrue(
            executor.validate_artifact_manifest(candidate, executor.load_registry())
        )

        self.run_cmd(
            "commit", "--output", str(self.output), "--transaction", transaction
        )
        committed = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(committed["artifact_manifest_status"], "valid")
        self.assertEqual(committed["artifact_manifest_stale_reasons"], [])
        self.assertEqual(committed["artifact_manifest_errors"], [])
        self.assertEqual(
            committed["candidate_artifact_manifest_status"], "not-applicable"
        )
        self.assertEqual(committed["manifest_refresh_pending"], "none")

    def test_stage_validate_is_read_only_and_separates_expected_manifest_drift(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.complete_checkpoints(transaction)
        before = raw_tree_hashes(self.output)

        result = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["stage_validation_report_schema_version"], "1")
        self.assertEqual(payload["result"], "ready")
        self.assertEqual(payload["semantic_or_document_errors"]["count"], 0)
        self.assertEqual(payload["blocking_errors"]["count"], 0)
        self.assertEqual(
            payload["expected_candidate_manifest_drift"]["status"],
            "pending-refresh",
        )
        self.assertTrue(
            payload["expected_candidate_manifest_drift"]["refresh_on_commit"]
        )
        self.assertTrue(
            any(
                "evidence-index.json" in reason
                for reason in payload["expected_candidate_manifest_drift"]["reasons"]
            )
        )
        self.assertLess(len(result.stdout.encode("utf-8")), 10_000)
        self.assertEqual(raw_tree_hashes(self.output), before)

    def test_scaffold_creates_identity_correct_artifact_and_never_overwrites(self) -> None:
        inventory, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", inventory)

        tracing, candidate = self.begin("tracing")
        for identity_arguments, expected_message in (
            ([], "missing identity"),
            (["behavior_id=sample-repo.one", "behavior_id=sample-repo.two"], "duplicate"),
            (["unknown_id=sample-repo.one"], "missing identity"),
            (["behavior_id=../escape"], "portable characters"),
        ):
            with self.subTest(identity_arguments=identity_arguments):
                command = [
                    "scaffold",
                    "--output",
                    str(self.output),
                    "--transaction",
                    tracing,
                    "--artifact-type",
                    "behavior-dossier",
                ]
                for identity_argument in identity_arguments:
                    command.extend(["--identity", identity_argument])
                failure = json.loads(self.run_cmd(*command, expected=2).stdout)
                self.assertIn(expected_message, failure["error"])
        protected = [
            self.output / ".work" / "analysis-state.yaml",
            self.output / ".work" / "artifact-manifest.json",
            self.output / ".work" / "execution" / "active.lock",
            self.output
            / ".work"
            / "execution"
            / "transactions"
            / tracing
            / "transaction.json",
            self.output
            / ".work"
            / "execution"
            / "transactions"
            / tracing
            / "checkpoints.json",
            candidate / ".work" / "analysis-state.yaml",
            candidate / ".work" / "artifact-manifest.json",
        ]
        before = {path: path.read_bytes() for path in protected}
        result = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                tracing,
                "--artifact-type",
                "behavior-dossier",
                "--identity",
                "behavior_id=sample-repo.update-customer",
            ).stdout
        )
        self.assertEqual(result["result"], "created")
        self.assertEqual(result["candidate_manifest_status"], "stale")
        self.assertEqual(
            result["relative_path"],
            ".work/behavior-dossiers/sample-repo.update-customer.md",
        )
        dossier = Path(result["path"])
        dossier_text = dossier.read_text(encoding="utf-8")
        self.assertIn('artifact_type: "behavior-dossier"', dossier_text)
        self.assertIn('artifact_schema_version: "1"', dossier_text)
        self.assertIn('behavior_id: "sample-repo.update-customer"', dossier_text)
        self.assertIn('repository: "sample-repo"', dossier_text)
        self.assertIn('source_commit: "unknown"', dossier_text)
        self.assertIn('entry_type: "api|sqs|sns|eventbridge', dossier_text)
        self.assertEqual({path: path.read_bytes() for path in protected}, before)

        dossier.write_text(
            dossier_text.replace(
                "# Behavior working dossier", "# Analyst-written behavior dossier"
            ),
            encoding="utf-8",
        )
        edited_hash = hashlib.sha256(dossier.read_bytes()).hexdigest()
        existing = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                tracing,
                "--artifact-type",
                "behavior-dossier",
                "--identity",
                "behavior_id=sample-repo.update-customer",
            ).stdout
        )
        self.assertEqual(existing["result"], "already-exists")
        self.assertEqual(hashlib.sha256(dossier.read_bytes()).hexdigest(), edited_hash)

        dossier.write_text(
            dossier.read_text(encoding="utf-8").replace(
                'behavior_id: "sample-repo.update-customer"',
                'behavior_id: "sample-repo.conflict"',
            ),
            encoding="utf-8",
        )
        conflicting = dossier.read_bytes()
        conflict = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                tracing,
                "--artifact-type",
                "behavior-dossier",
                "--identity",
                "behavior_id=sample-repo.update-customer",
                expected=2,
            ).stdout
        )
        self.assertEqual(conflict["result"], "error")
        self.assertIn("identity conflicts", conflict["error"])
        self.assertEqual(dossier.read_bytes(), conflicting)

    def test_scaffold_rejects_wrong_stage_identity_and_lock_ownership(self) -> None:
        inventory, _candidate = self.begin("inventory")
        wrong_stage = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                inventory,
                "--artifact-type",
                "behavior-dossier",
                "--identity",
                "behavior_id=sample-repo.behavior",
                expected=2,
            ).stdout
        )
        self.assertIn("belongs to stage tracing", wrong_stage["error"])
        unsupported = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                inventory,
                "--artifact-type",
                "evidence-index",
                expected=2,
            ).stdout
        )
        self.assertIn("not scaffoldable", unsupported["error"])

        lock_path = self.output / ".work" / "execution" / "active.lock"
        lock = lock_path.read_text(encoding="utf-8")
        lock_path.write_text(lock.replace(inventory, "different-transaction"), encoding="utf-8")
        lock_error = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                inventory,
                "--artifact-type",
                "repository-synthesis",
                expected=2,
            ).stdout
        )
        self.assertIn("execution lock", lock_error["error"])
        lock_path.write_text(lock, encoding="utf-8")

        self.run_cmd("abort", "--output", str(self.output), "--transaction", inventory)
        absent = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                inventory,
                "--artifact-type",
                "repository-synthesis",
                expected=2,
            ).stdout
        )
        self.assertEqual(absent["result"], "error")

    def test_stage_validate_reports_checkpoint_and_invalid_manifest_blockers(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"999"}\n',
            encoding="utf-8",
        )
        result = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "blocked")
        codes = {item["code"] for item in payload["blocking_errors"]["items"]}
        self.assertIn("CHECKPOINT-INCOMPLETE", codes)
        self.assertIn("CANDIDATE-MANIFEST", codes)
        self.assertEqual(
            payload["expected_candidate_manifest_drift"]["status"], "none"
        )

    def test_stage_validate_detects_formal_drift_without_restoring_it(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.complete_checkpoints(transaction)
        register = self.output / ".work" / "repository-register.md"
        register.write_text(
            register.read_text(encoding="utf-8") + "\nUnexpected formal edit.\n",
            encoding="utf-8",
        )
        before = raw_tree_hashes(self.output)
        result = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertTrue(
            any(
                item["code"] == "FORMAL-DRIFT"
                for item in payload["blocking_errors"]["items"]
            )
        )
        self.assertEqual(raw_tree_hashes(self.output), before)

    def test_stage_validate_can_rerun_after_failed_commit(self) -> None:
        transaction, candidate = self.begin("inventory")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        result = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
        )
        self.assertEqual(json.loads(result.stdout)["result"], "ready")

    def test_stage_validate_json_error_uses_compact_report(self) -> None:
        result = self.run_cmd(
            "validate",
            "--output",
            str(self.output),
            "--transaction",
            "missing-transaction",
            expected=2,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "error")
        self.assertEqual(payload["blocking_errors"]["count"], 1)
        self.assertEqual(
            payload["blocking_errors"]["items"][0]["code"],
            "VALIDATION-COMMAND",
        )

    def test_stage_validator_parser_preserves_counts_and_classifies_diagnostics(self) -> None:
        executor = load_executor_module()
        pack_result = {
            "command": ["python3", "/skill/scripts/validate_pack_links.py"],
            "exit_code": 1,
            "stdout": json.dumps(
                {
                    "errors": {
                        "DEP-DOCUMENT": ["invalid Criticality value"],
                        "FAIL-DOCUMENT": ["invalid Retry Safety value"],
                        "MARKDOWN-FRAGMENT": [
                            "fragment target does not exist: tech-pack/a.md:8 -> b.md#missing"
                        ],
                    },
                    "primary_errors": 14,
                    "skipped": {
                        "FAIL-DEP-XREF": "Dependency Register is invalid"
                    },
                    "warnings": 3,
                    "warning_messages": ["one visible warning"],
                    "deferred_link_count": 2,
                    "deferred_links": [
                        {
                            "check": "api-materialization",
                            "source": "tech-pack/behaviors/get.md",
                            "target": "tech-pack/contracts/get.api-contract.md",
                        },
                        {
                            "check": "ba-traceability",
                            "source": "tech-pack/behaviors/get.md",
                            "target": "ba-pack/scenarios/get.md",
                        },
                    ],
                }
            ),
            "stderr": "",
        }
        (
            semantic,
            blocking,
            warnings,
            forward,
            forward_total,
            semantic_total,
            warning_total,
        ) = executor.parse_validator_diagnostics(pack_result)
        self.assertEqual(
            {item["code"] for item in semantic},
            {
                "DEP-DOCUMENT",
                "FAIL-DOCUMENT",
                "MARKDOWN-FRAGMENT",
                "SKIPPED:FAIL-DEP-XREF",
            },
        )
        self.assertEqual(blocking, [])
        self.assertEqual(len(warnings), 1)
        self.assertEqual(len(forward), 2)
        self.assertEqual(forward_total, 2)
        self.assertEqual(semantic_total, 15)
        self.assertEqual(warning_total, 3)

        text_result = {
            "command": ["python3", "/skill/scripts/validate_behavior_doc.py"],
            "exit_code": 1,
            "stdout": (
                "ERROR: missing document link\n"
                "ERROR [API-TABLE] line 12: invalid table\n"
                "WARNING: limited evidence\n"
            ),
            "stderr": "",
        }
        semantic, blocking, warnings, forward, forward_total, _, _ = (
            executor.parse_validator_diagnostics(text_result)
        )
        self.assertEqual(
            {item["code"] for item in semantic},
            {"DOCUMENT-VALIDATION", "API-TABLE"},
        )
        self.assertEqual(blocking, [])
        self.assertEqual(warnings[0]["code"], "VALIDATOR-WARNING")
        self.assertEqual(forward, [])
        self.assertEqual(forward_total, 0)

        maturity_result = {
            "command": ["python3", "/skill/scripts/validate_publication_maturity.py"],
            "exit_code": 1,
            "stdout": json.dumps(
                {
                    "publication_maturity_validation_version": "1",
                    "blocking_count": 1,
                    "review_count": 2,
                    "blocking_residues": [
                        {
                            "code": "DOC-PUBLICATION-RESIDUE",
                            "path": "tech-pack/behaviors/get.md",
                            "line": 12,
                            "message": "reader text exposes an execution-time forward reference",
                        }
                    ],
                    "review_terms": [
                        {
                            "code": "DOC-PUBLICATION-TERM",
                            "path": "ba-pack/scenarios/approval.md",
                            "line": 8,
                            "message": "review domain wording",
                        }
                    ],
                }
            ),
            "stderr": "",
        }
        semantic, blocking, warnings, _forward, _forward_total, semantic_total, warning_total = (
            executor.parse_validator_diagnostics(maturity_result)
        )
        self.assertEqual(semantic[0]["code"], "DOC-PUBLICATION-RESIDUE")
        self.assertEqual(semantic[0]["path"], "tech-pack/behaviors/get.md")
        self.assertEqual(semantic[0]["line"], 12)
        self.assertEqual(blocking, [])
        self.assertEqual(warnings[0]["code"], "DOC-PUBLICATION-TERM")
        self.assertEqual(semantic_total, 1)
        self.assertEqual(warning_total, 2)

    def test_stage_validation_semantic_projection_is_precommit_only(self) -> None:
        executor = load_executor_module()
        state = self.output / ".work" / "analysis-state.yaml"
        original = state.read_text(encoding="utf-8")
        projected, errors = executor.projected_validation_state(
            "synthesis", self.output
        )
        self.assertEqual(errors, [])
        self.assertEqual(executor.scalar_value(projected, "synthesis_status"), "complete")
        self.assertEqual(state.read_text(encoding="utf-8"), original)

        model = self.output / ".work" / "business-model.md"
        for status in ("complete", "partial", "blocked"):
            with self.subTest(status=status):
                model.write_text(
                    "---\n"
                    'artifact_type: "business-model"\n'
                    'artifact_schema_version: "1"\n'
                    f'business_model_status: "{status}"\n'
                    "---\n",
                    encoding="utf-8",
                )
                projected, errors = executor.projected_validation_state(
                    "business-model", self.output
                )
                self.assertEqual(errors, [])
                self.assertEqual(
                    executor.scalar_value(projected, "business_model_status"), status
                )

    def test_status_marks_invalid_candidate_artifact_identity(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"999"}\n',
            encoding="utf-8",
        )
        status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(status["artifact_manifest_status"], "stale")
        self.assertEqual(status["candidate_artifact_manifest_status"], "invalid")
        self.assertEqual(status["candidate_artifact_manifest_stale_reasons"], [])
        self.assertTrue(
            any(
                "artifact metadata mismatch: .work/evidence-index.json" in error
                for error in status["candidate_artifact_manifest_errors"]
            )
        )
        self.assertEqual(status["manifest_refresh_pending"], "formal")
        self.assertTrue(
            any("Artifact Schema:" in requirement for requirement in status["requirements"])
        )
        self.run_cmd(
            "abort", "--output", str(self.output), "--transaction", transaction
        )
        aborted = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(aborted["artifact_manifest_status"], "valid")
        self.assertEqual(aborted["manifest_refresh_pending"], "none")

    def test_candidate_registered_modification_and_deletion_are_stale(self) -> None:
        transaction, candidate = self.begin("inventory")
        register = candidate / ".work" / "repository-register.md"
        register.write_text(
            register.read_text(encoding="utf-8") + "\nInventory observation.\n",
            encoding="utf-8",
        )
        modified = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(modified["candidate_artifact_manifest_status"], "stale")
        self.assertIn(
            "artifact manifest checksum differs from file: "
            ".work/repository-register.md",
            modified["candidate_artifact_manifest_stale_reasons"],
        )
        self.assertEqual(modified["candidate_artifact_manifest_errors"], [])

        catalog = candidate / ".work" / "behavior-catalog.yaml"
        catalog.unlink()
        deleted = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(deleted["candidate_artifact_manifest_status"], "stale")
        self.assertIn(
            "artifact manifest references a missing file: "
            ".work/behavior-catalog.yaml",
            deleted["candidate_artifact_manifest_stale_reasons"],
        )
        self.assertEqual(deleted["candidate_artifact_manifest_errors"], [])
        self.run_cmd(
            "abort", "--output", str(self.output), "--transaction", transaction
        )

    def test_checkpoint_and_failed_commit_keep_manifest_diagnostics_separate(self) -> None:
        transaction, _candidate = self.begin("inventory")
        self.run_cmd(
            "checkpoint",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            "--checkpoint",
            "project-detection",
            "--status",
            "complete",
        )
        checkpoint_status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(checkpoint_status["artifact_manifest_status"], "stale")
        self.assertEqual(
            checkpoint_status["candidate_artifact_manifest_status"], "stale"
        )
        self.assertEqual(checkpoint_status["manifest_refresh_pending"], "both")
        self.assertEqual(checkpoint_status["artifact_manifest_errors"], [])
        self.assertEqual(checkpoint_status["candidate_artifact_manifest_errors"], [])

        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        failed = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(failed["artifact_manifest_status"], "stale")
        self.assertEqual(failed["candidate_artifact_manifest_status"], "valid")
        self.assertEqual(failed["manifest_refresh_pending"], "formal")
        self.assertEqual(failed["artifact_manifest_errors"], [])
        self.assertEqual(failed["candidate_artifact_manifest_errors"], [])
        self.assertTrue(
            any("evidence-index.json" in requirement for requirement in failed["requirements"])
        )
        self.run_cmd(
            "abort", "--output", str(self.output), "--transaction", transaction
        )

    def test_resume_rejects_active_stale_transaction_without_migration_plan(self) -> None:
        transaction, _candidate = self.begin("inventory")
        result = self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
            expected=2,
        )
        self.assertIn("status, commit, abort, or recover", result.stderr)
        self.assertFalse((self.output / ".work" / "migration-plan.yaml").exists())
        self.run_cmd(
            "abort", "--output", str(self.output), "--transaction", transaction
        )

    def test_commit_rejects_incomplete_checkpoints(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(EXECUTOR),
                "commit",
                "--output",
                str(self.output),
                "--transaction",
                transaction,
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("incomplete checkpoints", result.stderr)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_formal_drift_is_restored_and_commit_is_rejected(self) -> None:
        original = (self.output / ".work" / "repository-register.md").read_bytes()
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        (self.output / ".work" / "repository-register.md").write_text(
            original.decode("utf-8") + "\nUnauthorized formal write.\n",
            encoding="utf-8",
        )
        drift_status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(drift_status["artifact_manifest_status"], "invalid")
        self.assertEqual(drift_status["artifact_manifest_stale_reasons"], [])
        self.assertTrue(
            any(
                "unexpected formal Artifact Manifest drift" in error
                and ".work/repository-register.md" in error
                for error in drift_status["artifact_manifest_errors"]
            )
        )
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            transaction,
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertIn("FORMAL-DRIFT-RESTORED", " ".join(payload["errors"]))
        self.assertEqual(
            (self.output / ".work" / "repository-register.md").read_bytes(), original
        )
        self.assertTrue(candidate.is_dir())
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_recover_restores_interrupted_generation_swap(self) -> None:
        module = load_executor_module()
        transaction_id = "03-synthesis-interrupted"
        generation_id = "gen-interrupted"
        generation = self.output / ".work" / "execution" / "generations" / generation_id
        current_root = generation / "candidate-root"
        current_root.mkdir(parents=True)
        (current_root / "old.md").write_text("old generation\n", encoding="utf-8")
        tx_dir = self.output / ".work" / "execution" / "transactions" / transaction_id
        candidate = tx_dir / "candidate"
        candidate.mkdir(parents=True)
        (candidate / "new.md").write_text("new generation\n", encoding="utf-8")
        previous = generation / f"previous-{transaction_id}"
        current_root.rename(previous)
        state_path = self.output / ".work" / "analysis-state.yaml"
        original_state = state_path.read_text(encoding="utf-8")
        state = original_state
        state = module.set_scalar(state, "current_stage", "synthesis")
        state = module.set_scalar(state, "stage_status", "in-progress")
        state = module.set_scalar(state, "active_transaction", transaction_id)
        state = module.set_scalar(state, "current_checkpoint", "endpoint-reconciliation")
        state = module.set_scalar(state, "checkpoint_status", "in-progress")
        state_path.write_text(state, encoding="utf-8")
        (tx_dir / "pre-state.yaml").write_text(original_state, encoding="utf-8")
        (tx_dir / "transaction.json").write_text(
            json.dumps(
                {
                    "transaction_id": transaction_id,
                    "stage": "synthesis",
                    "status": "generation-promoting",
                    "candidate": str(candidate),
                }
            ),
            encoding="utf-8",
        )
        (tx_dir / "promotion-journal.json").write_text(
            json.dumps(
                {
                    "transaction_id": transaction_id,
                    "phase": "generation-old-moved",
                    "generation_id": generation_id,
                    "current_root": str(current_root),
                    "previous_root": str(previous),
                    "candidate": str(candidate),
                    "operations": [],
                }
            ),
            encoding="utf-8",
        )
        module.acquire_lock(
            self.output,
            {"transaction_id": transaction_id, "stage": "synthesis"},
        )
        recovered = self.run_cmd("recover", "--output", str(self.output))
        self.assertEqual(json.loads(recovered.stdout)["result"], "rolled-back-generation")
        self.assertEqual((current_root / "old.md").read_text(), "old generation\n")
        self.assertEqual((candidate / "new.md").read_text(), "new generation\n")
        recovered_state = state_path.read_text(encoding="utf-8")
        self.assertIn('stage_status: "failed"', recovered_state)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction_id)

    def test_second_begin_is_rejected_until_active_transaction_finishes(self) -> None:
        transaction, _candidate = self.begin("inventory")
        self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "inventory",
            expected=2,
        )
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)
        formal = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('stage_status: "pending"', formal)
        self.assertIn("active_transaction: null", formal)
        self.assertFalse((self.output / ".work" / "execution" / "active.lock").exists())

    def test_executor_does_not_modify_writable_skill_scripts(self) -> None:
        protected = [
            EXECUTOR,
            SKILL_ROOT / "scripts" / "artifact_schema.py",
            SKILL_ROOT / "scripts" / "artifact_scaffold.py",
            SKILL_ROOT / "scripts" / "validate_analysis_state.py",
            SKILL_ROOT / "scripts" / "build_evidence_index.py",
            SKILL_ROOT / "scripts" / "register_schema.py",
            SKILL_ROOT / "scripts" / "validate_pack_links.py",
            SKILL_ROOT / "assets" / "register-schema.json",
            SKILL_ROOT / "assets" / "artifact-schema.json",
            SKILL_ROOT / "assets" / "artifact-scaffold-schema.json",
            SKILL_ROOT / "assets" / "repository-register-template.md",
        ]
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
        }
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)
        tracing, _candidate = self.begin("tracing")
        self.run_cmd(
            "scaffold",
            "--output",
            str(self.output),
            "--transaction",
            tracing,
            "--artifact-type",
            "behavior-dossier",
            "--identity",
            "behavior_id=sample-repo.read-only-proof",
        )
        self.run_cmd("abort", "--output", str(self.output), "--transaction", tracing)
        after = {
            path: hashlib.sha256(path.read_bytes()).hexdigest() for path in protected
        }
        self.assertEqual(before, after)

    def test_executor_initializes_output_from_read_only_skill_copy(self) -> None:
        read_only_skill = self.root / "read-only-skill"
        shutil.copytree(
            SKILL_ROOT,
            read_only_skill,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        try:
            for path in sorted(read_only_skill.rglob("*"), reverse=True):
                path.chmod(0o555 if path.is_dir() else 0o444)
            read_only_skill.chmod(0o555)
            output = self.root / "read-only-output"
            result = subprocess.run(
                [
                    sys.executable,
                    str(read_only_skill / "scripts" / "stage_executor.py"),
                    "init",
                    "--repo",
                    str(self.repo),
                    "--output",
                    str(output),
                    "--json",
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((output / ".work" / "analysis-state.yaml").is_file())
        finally:
            read_only_skill.chmod(0o755)
            for path in read_only_skill.rglob("*"):
                path.chmod(0o755 if path.is_dir() else 0o644)

    def test_mark_behavior_requires_main_transaction_and_existing_dossier(self) -> None:
        transaction, candidate = self.begin("inventory")
        state = candidate / ".work" / "analysis-state.yaml"
        state.write_text(
            state.read_text(encoding="utf-8").replace(
                "behaviors: []",
                'behaviors:\n  - behavior_id: "sample-repo.handle-request"\n'
                '    status: "discovered"\n    dossier: null\n    notes: null',
            ),
            encoding="utf-8",
        )
        catalog = candidate / ".work" / "behavior-catalog.yaml"
        catalog.write_text(
            catalog.read_text(encoding="utf-8").replace(
                "behaviors: []",
                'behaviors:\n  - behavior_id: "sample-repo.handle-request"\n'
                '    status: "documented"\n    document: "behaviors/sample-repo.handle-request.md"',
            ),
            encoding="utf-8",
        )
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, tracing_candidate = self.begin("tracing")
        dossier = tracing_candidate / ".work" / "behavior-dossiers" / "sample-repo.handle-request.md"
        dossier.write_text(
            "---\n"
            'artifact_type: "behavior-dossier"\n'
            'artifact_schema_version: "1"\n'
            'behavior_id: "sample-repo.handle-request"\n'
            "---\n",
            encoding="utf-8",
        )
        self.run_cmd(
            "mark-behavior",
            "--output",
            str(self.output),
            "--transaction",
            tracing,
            "--behavior-id",
            "sample-repo.handle-request",
            "--status",
            "understood",
            "--dossier",
            "behavior-dossiers/sample-repo.handle-request.md",
        )
        candidate_state = (tracing_candidate / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        formal_state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('status: "understood"', candidate_state)
        self.assertIn('status: "discovered"', formal_state)
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)
        final_state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "synthesis"', final_state)
        self.assertIn('status: "understood"', final_state)

    def test_changed_files_are_archived_with_checksums(self) -> None:
        original_register = (self.output / ".work" / "repository-register.md").read_text(
            encoding="utf-8"
        )
        transaction, candidate = self.begin("inventory")
        register = candidate / ".work" / "repository-register.md"
        register.write_text(register.read_text(encoding="utf-8") + "\nInventory note.\n", encoding="utf-8")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        result = self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)
        receipt_path = Path(json.loads(result.stdout)["receipt"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        archive = Path(receipt["archive"])
        archived_register = archive / ".work" / "repository-register.md"
        self.assertEqual(archived_register.read_text(encoding="utf-8"), original_register)
        archive_manifest = json.loads((archive / "archive-manifest.json").read_text(encoding="utf-8"))
        self.assertIn(".work/repository-register.md", archive_manifest["files"])
        status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertTrue(status["archive_audits"])
        self.assertTrue(all(item["valid"] for item in status["archive_audits"]))

    def test_legacy_ba_directory_is_archived_only_by_migration(self) -> None:
        legacy = self.output / "ba-pack" / "behaviors"
        legacy.mkdir(parents=True)
        (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
        (self.output / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        planned = self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
        )
        plan_payload = json.loads(planned.stdout)
        self.assertEqual(plan_payload["resume_stage_after_migration"], "business-model")
        self.assertTrue(legacy.is_dir())
        begun = self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "migration",
            "--plan",
            str(self.output / ".work" / "migration-plan.yaml"),
        )
        begin_payload = json.loads(begun.stdout)
        candidate = Path(begin_payload["candidate"])
        self.assertFalse((candidate / "ba-pack" / "behaviors" / "old.md").exists())
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            begin_payload["transaction_id"],
        )
        receipt = json.loads(
            Path(json.loads(result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        archive = Path(receipt["archive"])
        self.assertEqual((archive / "ba-pack" / "behaviors" / "old.md").read_text(), "legacy\n")
        self.assertFalse((self.output / "ba-pack" / "behaviors").exists())
        self.assertEqual(receipt["stage"], "migration")

    def test_publication_stage_never_performs_legacy_ba_migration(self) -> None:
        legacy = self.output / "ba-pack" / "behaviors"
        legacy.mkdir(parents=True)
        (legacy / "old.md").write_text("legacy\n", encoding="utf-8")
        self.run_cmd(
            "begin",
            "--output",
            str(self.output),
            "--stage",
            "inventory",
            expected=2,
        )
        self.assertTrue(legacy.is_dir())

    def test_resume_plans_unknown_pack_without_mutating_state(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        text = state.read_text(encoding="utf-8")
        for key in (
            "workflow_schema_version",
            "repository_path",
            "current_stage",
            "stage_status",
            "active_transaction",
            "last_committed_stage",
        ):
            text = "\n".join(
                line for line in text.splitlines() if not line.startswith(key + ":")
            ) + "\n"
        text = text.replace('phase: "inventory"', 'phase: "completed"')
        text = text.replace('publication_status: "pending"', 'publication_status: "complete"')
        state.write_text(text, encoding="utf-8")
        before = state.read_bytes()
        result = self.run_cmd(
            "resume", "--repo", str(self.repo), "--state", str(state), expected=1
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], "migration-blocked")
        self.assertIn("current_stage", " ".join(payload["blocked_reasons"]))
        self.assertEqual(state.read_bytes(), before)
        self.assertTrue((self.output / ".work" / "migration-plan.yaml").is_file())

    def test_unversioned_register_creates_synthesis_migration_plan(self) -> None:
        (self.output / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        register = self.output / ".work" / "repository-register.md"
        register.write_text(
            "\n".join(
                line
                for line in register.read_text(encoding="utf-8").splitlines()
                if not line.startswith(("artifact_type:", "artifact_schema_version:"))
            )
            + "\n",
            encoding="utf-8",
        )
        result = self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["resume_stage_after_migration"], "synthesis")
        plan = json.loads((self.output / ".work" / "migration-plan.yaml").read_text())
        register_steps = [
            step for step in plan["steps"] if step["artifact_type"] == "repository-register"
        ]
        self.assertEqual(register_steps[0]["source_version"], "unknown")
        self.assertEqual(register_steps[0]["action"], "archive-and-rebuild")
        self.assertEqual(
            register_steps[0]["reinitialize_from_template"],
            "repository-register-template.md",
        )

    def test_recover_rolls_back_an_interrupted_promotion(self) -> None:
        transaction, _candidate = self.begin("inventory")
        partial = self.output / "partial-publication.md"
        partial.write_text("partial\n", encoding="utf-8")
        tx_dir = self.output / ".work" / "execution" / "transactions" / transaction
        journal_path = tx_dir / "promotion-journal.json"
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        journal.update(
            {
                "phase": "promoting",
                "archive": None,
                "operations": [{"kind": "add", "path": "partial-publication.md"}],
                "completed_operations": [
                    {"kind": "add", "path": "partial-publication.md"}
                ],
            }
        )
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        result = self.run_cmd("recover", "--output", str(self.output))
        self.assertEqual(json.loads(result.stdout)["result"], "rolled-back")
        self.assertFalse(partial.exists())
        state = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "inventory"', state)
        self.assertIn('stage_status: "failed"', state)
        self.assertIn(f'active_transaction: "{transaction}"', state)
        self.run_cmd("abort", "--output", str(self.output), "--transaction", transaction)

    def test_completed_state_requires_a_finalization_receipt(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        module = load_executor_module()
        text = state.read_text(encoding="utf-8")
        for key, value in (
            ("current_stage", "completed"),
            ("stage_status", "committed"),
            ("active_transaction", None),
            ("last_committed_stage", "finalization"),
            ("synthesis_status", "complete"),
            ("business_model_status", "blocked"),
            ("publication_status", "complete"),
            ("working_generation_id", "gen-completed"),
            ("published_generation_id", "gen-completed"),
            ("published_source_commit", "unknown"),
        ):
            text = module.set_scalar(text, key, value)
        state.write_text(text, encoding="utf-8")
        validator = SKILL_ROOT / "scripts" / "validate_analysis_state.py"
        command = [
            sys.executable,
            str(validator),
            str(state),
            "--repo",
            str(self.repo),
            "--catalog",
            str(self.output / ".work" / "behavior-catalog.yaml"),
            "--dossiers-dir",
            str(self.output / ".work" / "behavior-dossiers"),
        ]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("finalization receipt", missing.stdout)
        receipt = self.output / ".work" / "execution" / "receipts" / "999-finalization.json"
        receipt.write_text(
            json.dumps(
                {
                    "artifact_type": "stage-receipt",
                    "artifact_schema_version": "2",
                    "stage": "finalization",
                    "result": "committed",
                    "promotion_scope": "formal-pack",
                    "formal_pack_published": True,
                    "generation_id": "gen-completed",
                }
            ),
            encoding="utf-8",
        )
        valid = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(valid.returncode, 0, msg=valid.stdout + valid.stderr)

    def test_status_reports_completed_state_without_receipt_as_corrupt(self) -> None:
        state = self.output / ".work" / "analysis-state.yaml"
        module = load_executor_module()
        text = state.read_text(encoding="utf-8")
        text = module.set_scalar(text, "current_stage", "completed")
        text = module.set_scalar(text, "stage_status", "committed")
        text = module.set_scalar(text, "last_committed_stage", "finalization")
        text = module.set_scalar(text, "publication_status", "complete")
        state.write_text(text, encoding="utf-8")
        payload = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertIn("finalization Receipt", " ".join(payload["integrity_errors"]))

    def test_java_and_node_inventory_forward_paths(self) -> None:
        fixtures = {
            "java-forward": (
                "src/main/java/example/Handler.java",
                "package example; public class Handler { public String handle(String value) { return value; } }\n",
            ),
            "node-forward": (
                "src/handler.js",
                "exports.handler = async (event) => ({ statusCode: 200, body: event.id });\n",
            ),
        }
        for name, (relative_source, source_text) in fixtures.items():
            with self.subTest(name=name):
                repo = self.root / name
                source = repo / relative_source
                source.parent.mkdir(parents=True)
                source.write_text(source_text, encoding="utf-8")
                output = self.root / f"{name}-knowledge"
                initialized = subprocess.run(
                    [
                        sys.executable,
                        str(EXECUTOR),
                        "init",
                        "--repo",
                        str(repo),
                        "--output",
                        str(output),
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(initialized.returncode, 0, initialized.stderr)
                begun = subprocess.run(
                    [
                        sys.executable,
                        str(EXECUTOR),
                        "begin",
                        "--output",
                        str(output),
                        "--stage",
                        "inventory",
                        "--json",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(begun.returncode, 0, begun.stderr)
                begin_payload = json.loads(begun.stdout)
                candidate = Path(begin_payload["candidate"])
                index = subprocess.run(
                    [
                        sys.executable,
                        str(SKILL_ROOT / "scripts" / "build_evidence_index.py"),
                        "--repo",
                        str(repo),
                        "--output",
                        str(candidate / ".work" / "evidence-index.json"),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(index.returncode, 0, index.stderr)
                committed = self.run_cmd(
                    "commit",
                    "--output",
                    str(output),
                    "--transaction",
                    begin_payload["transaction_id"],
                )
                self.assertEqual(committed.returncode, 0, committed.stdout + committed.stderr)
                state = (output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
                self.assertIn('current_stage: "tracing"', state)

    def test_complete_api_ba_lifecycle_publishes_consistent_generation(self) -> None:
        source = self.repo / "src" / "Handler.java"
        source.parent.mkdir(parents=True)
        source.write_text(
            "class Handler {\n"
            "  String getCustomer(String id) { return id; }\n"
            "  String putCustomer(String id) { return id; }\n"
            "}\n",
            encoding="utf-8",
        )
        executor = load_executor_module()

        inventory, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        state = candidate / ".work" / "analysis-state.yaml"
        state.write_text(
            state.read_text(encoding="utf-8").replace(
                "behaviors: []",
                "behaviors:\n"
                f'  - behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
                '    status: "discovered"\n'
                "    dossier: null\n"
                '    notes: "Two application routes share one observable behavior."',
            ),
            encoding="utf-8",
        )
        working_catalog = candidate / ".work" / "behavior-catalog.yaml"
        working_catalog.write_text(
            'artifact_type: "working-behavior-catalog"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            'analysis_mode: "automatic"\n'
            "behaviors:\n"
            f'  - behavior_id: "{COMPLETE_BEHAVIOR_ID}"\n'
            '    title: "Manage customer profile"\n'
            '    category: "business"\n'
            "    triggers:\n"
            '      - type: "api"\n'
            '        name: "GET or PUT /customers/{id}"\n'
            "    entry_points:\n"
            '      - "src/Handler.java:2"\n'
            '      - "src/Handler.java:3"\n'
            '    status: "discovered"\n'
            "    duplicate_of: null\n"
            f'    document: "behaviors/{COMPLETE_BEHAVIOR_ID}.md"\n'
            "    ba_scenarios: []\n"
            "    api_contracts:\n"
            + "".join(
                f'      - endpoint_id: "{endpoint_id}"\n'
                f'        document: "contracts/{endpoint_id}.api-contract.md"\n'
                for endpoint_id, _method, _route, _line in COMPLETE_ENDPOINTS
            )
            + "summary:\n"
            "  discovered: 1\n"
            "  documented: 0\n"
            "  technical: 0\n"
            "  duplicate: 0\n"
            "  excluded: 0\n"
            "  blocked: 0\n",
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", inventory)

        tracing, candidate = self.begin("tracing")
        scaffolded_dossier = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                tracing,
                "--artifact-type",
                "behavior-dossier",
                "--identity",
                f"behavior_id={COMPLETE_BEHAVIOR_ID}",
            ).stdout
        )
        self.assertEqual(scaffolded_dossier["result"], "created")
        dossier = (
            candidate
            / ".work"
            / "behavior-dossiers"
            / f"{COMPLETE_BEHAVIOR_ID}.md"
        )
        dossier.write_text(complete_dossier_fixture(), encoding="utf-8")
        self.run_cmd(
            "mark-behavior",
            "--output",
            str(self.output),
            "--transaction",
            tracing,
            "--behavior-id",
            COMPLETE_BEHAVIOR_ID,
            "--status",
            "understood",
            "--dossier",
            f"behavior-dossiers/{COMPLETE_BEHAVIOR_ID}.md",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)

        synthesis, candidate = self.begin("synthesis")
        (candidate / ".work" / "repository-register.md").write_text(
            complete_register_fixture(executor), encoding="utf-8"
        )
        scaffolded_synthesis = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                synthesis,
                "--artifact-type",
                "repository-synthesis",
            ).stdout
        )
        self.assertEqual(scaffolded_synthesis["result"], "created")
        (candidate / ".work" / "repository-synthesis.md").write_text(
            complete_repository_synthesis_fixture(executor), encoding="utf-8"
        )
        self.complete_checkpoints(synthesis)
        synthesis_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                synthesis,
            ).stdout
        )
        self.assertEqual(synthesis_validation["result"], "ready")
        self.assertFalse(
            any(
                "synthesis_status" in item["message"]
                for item in synthesis_validation["semantic_or_document_errors"]["items"]
            )
        )
        synthesis_result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            synthesis,
            "--semantic-result",
            "complete",
        )
        synthesis_receipt = json.loads(
            Path(json.loads(synthesis_result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        generation_id = synthesis_receipt["generation_id"]
        generation_root = (
            self.output
            / ".work"
            / "execution"
            / "generations"
            / generation_id
            / "candidate-root"
        )

        tech, candidate = self.begin("tech-publication")
        for artifact_type, identities in (
            ("tech-behavior", [f"behavior_id={COMPLETE_BEHAVIOR_ID}"]),
            ("repository-overview", []),
            ("tech-behavior-catalog", []),
        ):
            command = [
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                tech,
                "--artifact-type",
                artifact_type,
            ]
            for identity in identities:
                command.extend(["--identity", identity])
            scaffolded = json.loads(self.run_cmd(*command).stdout)
            self.assertEqual(scaffolded["result"], "created")
        (candidate / "tech-pack" / "behaviors" / f"{COMPLETE_BEHAVIOR_ID}.md").write_text(
            complete_api_behavior_fixture(include_ba=False), encoding="utf-8"
        )
        (candidate / "tech-pack" / "repository-overview.md").write_text(
            "---\n"
            'artifact_type: "repository-overview"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Repository overview\n\n"
            "The fixture provides the observed customer profile capability.\n",
            encoding="utf-8",
        )
        (candidate / "tech-pack" / "behavior-catalog.yaml").write_text(
            complete_tech_catalog_fixture(include_ba=False), encoding="utf-8"
        )
        self.assertFalse((candidate / "tech-pack" / "endpoint-matrix.md").exists())
        self.assertFalse((candidate / "tech-pack" / "contracts").exists())
        self.complete_checkpoints(tech)
        tech_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                tech,
            ).stdout
        )
        self.assertEqual(tech_validation["result"], "ready")
        self.assertGreaterEqual(
            tech_validation["cross_stage_forward_references"]["count"],
            len(COMPLETE_ENDPOINTS),
        )
        self.assertEqual(tech_validation["semantic_or_document_errors"]["count"], 0)
        self.assertEqual(tech_validation["blocking_errors"]["count"], 0)
        tech_result = self.run_cmd(
            "commit", "--output", str(self.output), "--transaction", tech
        )
        tech_receipt = json.loads(
            Path(json.loads(tech_result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        behavior_validator = next(
            result
            for result in tech_receipt["validators"]
            if any("validate_behavior_doc.py" in part for part in result["command"])
        )
        pack_validator = next(
            result
            for result in tech_receipt["validators"]
            if any("validate_pack_links.py" in part for part in result["command"])
        )
        self.assertIn("--allow-missing-api-contracts", behavior_validator["command"])
        self.assertEqual(behavior_validator["exit_code"], 0)
        self.assertEqual(
            pack_validator["command"][
                pack_validator["command"].index("--validation-profile") + 1
            ],
            "tech-publication",
        )
        pack_payload = json.loads(pack_validator["stdout"])
        self.assertEqual(pack_validator["exit_code"], 0)
        self.assertEqual(pack_payload["validation_profile"], "tech-publication")
        self.assertEqual(
            pack_payload["deferred_checks"],
            ["api-materialization", "ba-traceability"],
        )
        self.assertGreaterEqual(
            pack_payload["deferred_link_count"], len(COMPLETE_ENDPOINTS)
        )
        self.assertEqual(pack_payload["primary_errors"], 0)
        self.assertEqual(pack_payload["skipped_validation_groups"], 0)
        self.assertFalse((generation_root / "tech-pack" / "endpoint-matrix.md").exists())
        for endpoint_id, _method, _route, _line in COMPLETE_ENDPOINTS:
            self.assertFalse(
                (
                    generation_root
                    / "tech-pack"
                    / "contracts"
                    / f"{endpoint_id}.api-contract.md"
                ).exists()
            )

        api, candidate = self.begin("api-contract-publication")
        scaffolded_matrix = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                api,
                "--artifact-type",
                "endpoint-matrix",
            ).stdout
        )
        self.assertEqual(scaffolded_matrix["result"], "created")
        (candidate / "tech-pack" / "endpoint-matrix.md").write_text(
            complete_endpoint_matrix_fixture(), encoding="utf-8"
        )
        contracts = candidate / "tech-pack" / "contracts"
        first_endpoint = COMPLETE_ENDPOINTS[0]
        scaffolded_contract = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                api,
                "--artifact-type",
                "api-contract",
                "--identity",
                f"endpoint_id={first_endpoint[0]}",
                "--identity",
                f"behavior_id={COMPLETE_BEHAVIOR_ID}",
            ).stdout
        )
        self.assertEqual(scaffolded_contract["result"], "created")
        (contracts / f"{first_endpoint[0]}.api-contract.md").write_text(
            complete_api_contract_fixture(*first_endpoint), encoding="utf-8"
        )
        self.complete_checkpoints(api)
        incomplete_api_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                api,
                expected=1,
            ).stdout
        )
        self.assertEqual(incomplete_api_validation["result"], "blocked")
        self.assertGreater(
            incomplete_api_validation["semantic_or_document_errors"]["count"], 0
        )
        self.assertEqual(
            incomplete_api_validation["cross_stage_forward_references"]["count"], 0
        )
        failed_api = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            api,
            expected=1,
        )
        failed_payload = json.loads(failed_api.stdout)
        self.assertEqual(failed_payload["result"], "failed")
        self.assertTrue(candidate.is_dir())
        self.assertEqual(
            json.loads(
                (
                    self.output
                    / ".work"
                    / "execution"
                    / "generations"
                    / generation_id
                    / "generation-manifest.json"
                ).read_text(encoding="utf-8")
            )["last_committed_stage"],
            "tech-publication",
        )
        self.assertEqual(
            list(
                (self.output / ".work" / "execution" / "receipts").glob(
                    "*-api-contract-publication.json"
                )
            ),
            [],
        )
        transaction_record = json.loads(
            (
                self.output
                / ".work"
                / "execution"
                / "transactions"
                / api
                / "transaction.json"
            ).read_text(encoding="utf-8")
        )
        validator_output = "\n".join(
            result.get("stdout", "") + result.get("stderr", "")
            for result in transaction_record.get("validators", [])
        )
        missing_contract = f"{COMPLETE_ENDPOINTS[1][0]}.api-contract.md"
        self.assertIn(missing_contract, validator_output)

        second_endpoint = COMPLETE_ENDPOINTS[1]
        retry_scaffold = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                api,
                "--artifact-type",
                "api-contract",
                "--identity",
                f"endpoint_id={second_endpoint[0]}",
                "--identity",
                f"behavior_id={COMPLETE_BEHAVIOR_ID}",
            ).stdout
        )
        self.assertEqual(retry_scaffold["result"], "created")
        (contracts / f"{second_endpoint[0]}.api-contract.md").write_text(
            complete_api_contract_fixture(*second_endpoint), encoding="utf-8"
        )
        complete_api_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                api,
            ).stdout
        )
        self.assertEqual(complete_api_validation["result"], "ready")
        api_result = self.run_cmd(
            "commit", "--output", str(self.output), "--transaction", api
        )
        api_receipt = json.loads(
            Path(json.loads(api_result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        self.assertEqual(api_receipt["generation_id"], generation_id)
        for endpoint_id, _method, _route, _line in COMPLETE_ENDPOINTS:
            self.assertTrue(
                (
                    generation_root
                    / "tech-pack"
                    / "contracts"
                    / f"{endpoint_id}.api-contract.md"
                ).is_file()
            )

        business_model, candidate = self.begin("business-model")
        scaffolded_model = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                business_model,
                "--artifact-type",
                "business-model",
            ).stdout
        )
        self.assertEqual(scaffolded_model["result"], "created")
        (candidate / ".work" / "business-model.md").write_text(
            complete_business_model_fixture(executor), encoding="utf-8"
        )
        self.complete_checkpoints(business_model)
        model_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                business_model,
            ).stdout
        )
        self.assertEqual(model_validation["result"], "ready")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            business_model,
            "--semantic-result",
            "complete",
        )

        ba, candidate = self.begin("ba-publication")
        (candidate / "tech-pack" / "behaviors" / f"{COMPLETE_BEHAVIOR_ID}.md").write_text(
            complete_api_behavior_fixture(include_ba=True), encoding="utf-8"
        )
        (candidate / "tech-pack" / "behavior-catalog.yaml").write_text(
            complete_tech_catalog_fixture(include_ba=True), encoding="utf-8"
        )
        for artifact_type, identities in (
            ("ba-overview", []),
            ("ba-catalog", []),
            ("ba-journey", [f"journey_id={COMPLETE_JOURNEY_ID}"]),
            ("ba-scenario", [f"scenario_id={COMPLETE_SCENARIO_ID}"]),
        ):
            command = [
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                ba,
                "--artifact-type",
                artifact_type,
            ]
            for identity in identities:
                command.extend(["--identity", identity])
            scaffolded = json.loads(self.run_cmd(*command).stdout)
            self.assertEqual(scaffolded["result"], "created")
        (candidate / "ba-pack" / "business-overview.md").write_text(
            complete_ba_overview_fixture(), encoding="utf-8"
        )
        (candidate / "ba-pack" / "business-catalog.md").write_text(
            complete_ba_catalog_fixture(), encoding="utf-8"
        )
        (candidate / "ba-pack" / "journeys" / f"{COMPLETE_JOURNEY_ID}.md").write_text(
            complete_ba_journey_fixture(), encoding="utf-8"
        )
        (candidate / "ba-pack" / "scenarios" / f"{COMPLETE_SCENARIO_ID}.md").write_text(
            complete_ba_scenario_fixture(), encoding="utf-8"
        )
        self.complete_checkpoints(ba)
        ba_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                ba,
            ).stdout
        )
        self.assertEqual(ba_validation["result"], "ready")
        ba_result = self.run_cmd(
            "commit", "--output", str(self.output), "--transaction", ba
        )
        ba_receipt = json.loads(
            Path(json.loads(ba_result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        for validator_name in (
            "validate_behavior_doc.py",
            "validate_ba_journey.py",
            "validate_ba_scenario.py",
            "validate_pack_links.py",
        ):
            matching = [
                result
                for result in ba_receipt["validators"]
                if any(validator_name in part for part in result["command"])
            ]
            self.assertTrue(matching, validator_name)
            self.assertTrue(all(result["exit_code"] == 0 for result in matching))

        finalization, _candidate = self.begin("finalization")
        finalization_scaffold = json.loads(
            self.run_cmd(
                "scaffold",
                "--output",
                str(self.output),
                "--transaction",
                finalization,
                "--artifact-type",
                "repository-overview",
                expected=2,
            ).stdout
        )
        self.assertIn("not allowed during finalization", finalization_scaffold["error"])
        self.complete_checkpoints(finalization)
        final_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                finalization,
            ).stdout
        )
        self.assertEqual(final_validation["result"], "ready")
        finalized = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            finalization,
        )
        final_payload = json.loads(finalized.stdout)
        final_receipt = json.loads(
            Path(final_payload["receipt"]).read_text(encoding="utf-8")
        )
        status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertEqual(status["working_generation_id"], generation_id)
        self.assertEqual(status["published_generation_id"], generation_id)
        self.assertEqual(status["working_generation_status"], "published")
        self.assertEqual(status["release_readiness"], "ready")
        self.assertEqual(status["integrity_errors"], [])
        self.assertEqual(status["artifact_manifest_status"], "valid")
        self.assertEqual(status["artifact_manifest_stale_reasons"], [])
        self.assertEqual(status["artifact_manifest_errors"], [])
        self.assertEqual(
            status["candidate_artifact_manifest_status"], "not-applicable"
        )
        self.assertEqual(status["manifest_refresh_pending"], "none")

        self.assertEqual(final_receipt["result"], "committed")
        self.assertEqual(final_receipt["promotion_scope"], "formal-pack")
        self.assertTrue(final_receipt["formal_pack_published"])
        self.assertEqual(final_receipt["generation_id"], generation_id)
        self.assertEqual(final_receipt["primary_error_count"], 0)
        self.assertEqual(final_receipt["skipped_group_count"], 0)
        self.assertEqual(final_receipt["publication_maturity_validation_version"], "1")
        self.assertEqual(final_receipt["publication_maturity_blocking_count"], 0)
        self.assertEqual(final_receipt["publication_maturity_review_count"], 0)
        self.assertEqual(final_receipt["markdown_fragment_validation_version"], "1")
        self.assertGreater(final_receipt["markdown_fragment_checked_count"], 0)
        self.assertGreater(
            final_receipt["markdown_fragment_target_document_count"], 0
        )
        self.assertEqual(final_receipt["markdown_fragment_error_count"], 0)
        self.assertEqual(final_receipt["markdown_fragment_skipped_group_count"], 0)
        self.assertEqual(status["markdown_fragment_validation_status"], "current")

        artifact_manifest_path = self.output / ".work" / "artifact-manifest.json"
        artifact_manifest = json.loads(artifact_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(artifact_manifest["last_transaction"], finalization)
        self.assertEqual(executor.validate_artifact_manifest(self.output, executor.load_registry()), [])
        expected_artifacts = {
            ".work/business-model.md",
            "tech-pack/repository-overview.md",
            "tech-pack/behavior-catalog.yaml",
            f"tech-pack/behaviors/{COMPLETE_BEHAVIOR_ID}.md",
            "tech-pack/endpoint-matrix.md",
            *(f"tech-pack/contracts/{endpoint_id}.api-contract.md" for endpoint_id, *_rest in COMPLETE_ENDPOINTS),
            "ba-pack/business-overview.md",
            "ba-pack/business-catalog.md",
            f"ba-pack/journeys/{COMPLETE_JOURNEY_ID}.md",
            f"ba-pack/scenarios/{COMPLETE_SCENARIO_ID}.md",
        }
        manifest_entries = {
            entry["path"]: entry for entry in artifact_manifest["artifacts"]
        }
        self.assertTrue(expected_artifacts.issubset(manifest_entries))
        for relative in expected_artifacts:
            document = self.output / relative
            self.assertTrue(document.is_file(), relative)
            self.assertEqual(manifest_entries[relative]["sha256"], executor.sha256_file(document))

        generation_manifest = json.loads(
            (
                self.output
                / ".work"
                / "execution"
                / "generations"
                / generation_id
                / "generation-manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            generation_manifest["published_knowledge_manifest"],
            executor.knowledge_manifest(self.output),
        )

        independent = subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "validate_pack_links.py"),
                str(self.output),
                "--repo",
                str(self.repo),
                "--require-artifact-manifest",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        independent_payload = json.loads(independent.stdout)
        self.assertEqual(independent_payload["primary_errors"], 0)
        self.assertEqual(independent_payload["skipped_validation_groups"], 0)
        self.assertEqual(independent_payload["markdown_fragment_validation_version"], "1")
        self.assertGreater(independent_payload["checked_fragments"], 0)

        # Simulate a current-schema Pack finalized before publication-maturity
        # validation existed. Resume must request a transactional Finalization
        # revalidation rather than creating a Migration Plan.
        old_receipt_path = Path(final_payload["receipt"])
        old_receipt = json.loads(old_receipt_path.read_text(encoding="utf-8"))
        old_receipt.pop("publication_maturity_validation_version")
        old_receipt.pop("publication_maturity_blocking_count")
        old_receipt.pop("publication_maturity_review_count")
        old_receipt_path.write_text(
            json.dumps(old_receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        state_text = (self.output / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        executor.write_artifact_manifest(
            self.output,
            executor.load_registry(),
            str(self.repo),
            executor.scalar_value(state_text, "source_commit") or "unknown",
            "finalization",
            finalization,
            [],
        )
        before_resume = raw_tree_hashes(self.output)
        resume = self.run_cmd(
            "resume",
            "--repo",
            str(self.repo),
            "--state",
            str(self.output / ".work" / "analysis-state.yaml"),
        )
        resume_payload = json.loads(resume.stdout)
        self.assertEqual(resume_payload["result"], "revalidation-required")
        self.assertEqual(resume_payload["required_stage"], "finalization")
        self.assertFalse((self.output / ".work" / "migration-plan.yaml").exists())
        self.assertEqual(raw_tree_hashes(self.output), before_resume)

        formal_before_revalidation = executor.knowledge_manifest(self.output)
        revalidation, revalidation_candidate = self.begin("finalization")
        revalidation_transaction = json.loads(
            (
                self.output
                / ".work"
                / "execution"
                / "transactions"
                / revalidation
                / "transaction.json"
            ).read_text(encoding="utf-8")
        )
        revalidation_generation = revalidation_transaction["generation_id"]
        self.assertEqual(
            revalidation_transaction["revalidation_kind"], "publication-maturity"
        )
        self.assertNotEqual(revalidation_generation, generation_id)
        self.assertEqual(executor.knowledge_manifest(self.output), formal_before_revalidation)

        overview = revalidation_candidate / "tech-pack" / "repository-overview.md"
        durable_overview = overview.read_text(encoding="utf-8")
        overview.write_text(
            durable_overview + "\nThe API Contract is a forward reference.\n",
            encoding="utf-8",
        )
        self.complete_checkpoints(revalidation)
        blocked_revalidation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                revalidation,
                expected=1,
            ).stdout
        )
        self.assertTrue(
            any(
                item["code"] == "DOC-PUBLICATION-RESIDUE"
                for item in blocked_revalidation["semantic_or_document_errors"]["items"]
            )
        )
        failed_revalidation = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            revalidation,
            expected=1,
        )
        self.assertEqual(json.loads(failed_revalidation.stdout)["result"], "failed")
        self.assertEqual(executor.knowledge_manifest(self.output), formal_before_revalidation)

        overview.write_text(
            durable_overview
            + "\nThe API Contract documents the callable endpoint while customer approval is pending.\n",
            encoding="utf-8",
        )
        warning_validation = json.loads(
            self.run_cmd(
                "validate",
                "--output",
                str(self.output),
                "--transaction",
                revalidation,
            ).stdout
        )
        self.assertEqual(warning_validation["result"], "ready")
        self.assertTrue(
            any(
                item["code"] == "DOC-PUBLICATION-TERM"
                for item in warning_validation["warnings"]["items"]
            )
        )
        overview.write_text(
            durable_overview + "\nThe API Contract documents the callable endpoint.\n",
            encoding="utf-8",
        )
        committed_revalidation = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            revalidation,
        )
        committed_revalidation_payload = json.loads(committed_revalidation.stdout)
        revalidation_receipt = json.loads(
            Path(committed_revalidation_payload["receipt"]).read_text(encoding="utf-8")
        )
        self.assertEqual(
            revalidation_receipt["publication_maturity_validation_version"], "1"
        )
        self.assertEqual(revalidation_receipt["publication_maturity_blocking_count"], 0)
        revalidated_status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(revalidated_status["publication_maturity_status"], "current")
        self.assertEqual(revalidated_status["release_readiness"], "ready")
        self.assertEqual(
            revalidated_status["working_generation_id"], revalidation_generation
        )
        self.assertEqual(
            revalidated_status["published_generation_id"], revalidation_generation
        )
        revalidation_generation_root = (
            self.output
            / ".work"
            / "execution"
            / "generations"
            / revalidation_generation
            / "candidate-root"
        )
        self.assertEqual(
            executor.knowledge_manifest(revalidation_generation_root),
            executor.knowledge_manifest(self.output),
        )
        resumed_current = json.loads(
            self.run_cmd(
                "resume",
                "--repo",
                str(self.repo),
                "--state",
                str(self.output / ".work" / "analysis-state.yaml"),
            ).stdout
        )
        self.assertEqual(resumed_current["result"], "resume-ready")

        # An aborted revalidation restores the prior completed State and removes
        # the newly created Generation without touching the formal knowledge Pack.
        latest_receipt_path = Path(committed_revalidation_payload["receipt"])
        latest_receipt = json.loads(latest_receipt_path.read_text(encoding="utf-8"))
        latest_receipt.pop("publication_maturity_validation_version")
        latest_receipt.pop("publication_maturity_blocking_count")
        latest_receipt.pop("publication_maturity_review_count")
        latest_receipt_path.write_text(
            json.dumps(latest_receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        state_text = (self.output / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        executor.write_artifact_manifest(
            self.output,
            executor.load_registry(),
            str(self.repo),
            executor.scalar_value(state_text, "source_commit") or "unknown",
            "finalization",
            revalidation,
            [],
        )
        before_abort = executor.knowledge_manifest(self.output)
        abort_transaction, _abort_candidate = self.begin("finalization")
        abort_record = json.loads(
            (
                self.output
                / ".work"
                / "execution"
                / "transactions"
                / abort_transaction
                / "transaction.json"
            ).read_text(encoding="utf-8")
        )
        abort_generation = abort_record["generation_id"]
        self.run_cmd(
            "abort",
            "--output",
            str(self.output),
            "--transaction",
            abort_transaction,
        )
        aborted_status = json.loads(
            self.run_cmd("status", "--output", str(self.output)).stdout
        )
        self.assertEqual(aborted_status["current_stage"], "completed")
        self.assertEqual(executor.knowledge_manifest(self.output), before_abort)
        self.assertFalse(
            (
                self.output
                / ".work"
                / "execution"
                / "generations"
                / abort_generation
            ).exists()
        )

        # A Pack whose latest Finalization Receipt predates Markdown fragment
        # validation uses the same transactional revalidation boundary, not a
        # schema Migration.
        fragment_old_receipt = json.loads(
            latest_receipt_path.read_text(encoding="utf-8")
        )
        fragment_old_receipt["publication_maturity_validation_version"] = "1"
        fragment_old_receipt["publication_maturity_blocking_count"] = 0
        fragment_old_receipt["publication_maturity_review_count"] = 0
        for key in (
            "markdown_fragment_validation_version",
            "markdown_fragment_checked_count",
            "markdown_fragment_target_document_count",
            "markdown_fragment_error_count",
            "markdown_fragment_skipped_group_count",
        ):
            fragment_old_receipt.pop(key, None)
        latest_receipt_path.write_text(
            json.dumps(fragment_old_receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        state_text = (self.output / ".work" / "analysis-state.yaml").read_text(
            encoding="utf-8"
        )
        executor.write_artifact_manifest(
            self.output,
            executor.load_registry(),
            str(self.repo),
            executor.scalar_value(state_text, "source_commit") or "unknown",
            "finalization",
            revalidation,
            [],
        )
        fragment_resume = json.loads(
            self.run_cmd(
                "resume",
                "--repo",
                str(self.repo),
                "--state",
                str(self.output / ".work" / "analysis-state.yaml"),
            ).stdout
        )
        self.assertEqual(fragment_resume["result"], "revalidation-required")
        self.assertEqual(
            fragment_resume["reason"], "markdown-fragment-validation-outdated"
        )
        self.assertFalse((self.output / ".work" / "migration-plan.yaml").exists())
        fragment_revalidation, _fragment_candidate = self.begin("finalization")
        fragment_transaction = json.loads(
            (
                self.output
                / ".work"
                / "execution"
                / "transactions"
                / fragment_revalidation
                / "transaction.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            fragment_transaction["revalidation_kind"], "markdown-fragments"
        )
        self.run_cmd(
            "abort",
            "--output",
            str(self.output),
            "--transaction",
            fragment_revalidation,
        )

    def test_full_mechanical_stage_chain_requires_final_receipt(self) -> None:
        source = self.repo / "src" / "Handler.java"
        source.parent.mkdir(parents=True)
        source.write_text("class Handler {}\n", encoding="utf-8")

        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, _candidate = self.begin("tracing")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)

        synthesis, candidate = self.begin("synthesis")
        executor = load_executor_module()
        register_schema = json.loads(
            (SKILL_ROOT / "assets" / "register-schema.json").read_text(encoding="utf-8")
        )
        tables_by_section = {
            table["section"]: table["headers"]
            for table in register_schema["tables"].values()
        }
        register_parts = [
            "---",
            'artifact_type: "repository-register"',
            'artifact_schema_version: "1"',
            'repository: "sample-repo"',
            'source_commit: "unknown"',
            'register_status: "reconciled"',
            "---",
            "",
            "# Repository register",
        ]
        for heading in sorted(executor.REGISTER_HEADINGS):
            register_parts.extend(["", f"## {heading}", ""])
            headers = tables_by_section[heading]
            register_parts.append("| " + " | ".join(headers) + " |")
            register_parts.append("|" + "|".join("---" for _ in headers) + "|")
        register_text = "\n".join(register_parts) + "\n"
        synthesis_text = (
            "---\n"
            'artifact_type: "repository-synthesis"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Repository synthesis\n\n"
        ) + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.SYNTHESIS_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "repository-register.md").write_text(
            register_text, encoding="utf-8"
        )
        (candidate / ".work" / "repository-synthesis.md").write_text(
            synthesis_text, encoding="utf-8"
        )
        synthesis_result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            synthesis,
            "--semantic-result",
            "complete",
        )
        synthesis_receipt = json.loads(
            Path(json.loads(synthesis_result.stdout)["receipt"]).read_text(encoding="utf-8")
        )
        generation_id = synthesis_receipt["generation_id"]
        self.assertEqual(synthesis_receipt["promotion_scope"], "generation")
        self.assertFalse(synthesis_receipt["formal_pack_published"])
        self.assertFalse((self.output / ".work" / "repository-synthesis.md").exists())
        self.assertTrue(
            (
                self.output
                / ".work"
                / "execution"
                / "generations"
                / generation_id
                / "candidate-root"
                / ".work"
                / "repository-synthesis.md"
            ).is_file()
        )

        tech, candidate = self.begin("tech-publication")
        (candidate / "tech-pack" / "behaviors").mkdir(parents=True)
        (candidate / "tech-pack" / "behaviors" / "sample-repo.get-customer.md").write_text(
            api_behavior_fixture(), encoding="utf-8"
        )
        (candidate / "tech-pack" / "repository-overview.md").write_text(
            "---\n"
            'artifact_type: "repository-overview"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Repository overview\n\nThe fixture exposes one application route.\n",
            encoding="utf-8",
        )
        catalog_text = (
            'artifact_type: "tech-behavior-catalog"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            'analysis_mode: "automatic"\n'
            "behaviors:\n"
            '  - behavior_id: "sample-repo.get-customer"\n'
            '    title: "Get customer"\n'
            '    category: "business"\n'
            "    triggers:\n"
            '      - type: "api"\n'
            '        name: "GET /customers/{id}"\n'
            "    entry_points:\n"
            '      - "src/Handler.java:1"\n'
            '    status: "documented"\n'
            "    duplicate_of: null\n"
            '    document: "behaviors/sample-repo.get-customer.md"\n'
            "    ba_scenarios: []\n"
            "    api_contracts:\n"
            '      - endpoint_id: "sample-repo.get-customer"\n'
            '        document: "contracts/sample-repo.get-customer.api-contract.md"\n'
        )
        (candidate / "tech-pack" / "behavior-catalog.yaml").write_text(
            catalog_text, encoding="utf-8"
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tech)
        self.assertFalse((self.output / "tech-pack" / "repository-overview.md").exists())

        api, candidate = self.begin("api-contract-publication")
        (candidate / "tech-pack" / "endpoint-matrix.md").write_text(
            endpoint_matrix_fixture(), encoding="utf-8"
        )
        (candidate / "tech-pack" / "contracts").mkdir(parents=True)
        (
            candidate
            / "tech-pack"
            / "contracts"
            / "sample-repo.get-customer.api-contract.md"
        ).write_text(api_contract_fixture(), encoding="utf-8")
        self.run_cmd(
            "commit", "--output", str(self.output), "--transaction", api
        )

        model, candidate = self.begin("business-model")
        model_text = (
            "---\n"
            'artifact_type: "business-model"\n'
            'artifact_schema_version: "1"\n'
            'repository: "sample-repo"\n'
            'source_commit: "unknown"\n'
            "---\n\n"
            "# Business model\n\n"
        ) + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.BUSINESS_MODEL_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "business-model.md").write_text(model_text, encoding="utf-8")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            model,
            "--semantic-result",
            "blocked",
        )

        ba, _candidate = self.begin("ba-publication")
        self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            ba,
            "--skip",
            "--reason",
            "No safe business model can be published for this empty fixture.",
        )

        finalization, _candidate = self.begin("finalization")
        completed = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            finalization,
        )
        completed_payload = json.loads(completed.stdout)
        self.assertEqual(completed_payload["next_stage"], "completed")
        final_status = json.loads(self.run_cmd("status", "--output", str(self.output)).stdout)
        self.assertEqual(final_status["current_stage"], "completed")
        self.assertEqual(final_status["stage_status"], "committed")
        self.assertEqual(final_status["working_generation_status"], "published")
        self.assertEqual(final_status["working_generation_id"], generation_id)
        self.assertEqual(final_status["published_generation_id"], generation_id)
        self.assertEqual(final_status["release_readiness"], "ready")
        self.assertEqual(final_status["integrity_errors"], [])
        final_receipt = Path(completed_payload["receipt"])
        receipt_payload = json.loads(final_receipt.read_text(encoding="utf-8"))
        self.assertEqual(receipt_payload["stage"], "finalization")
        self.assertEqual(receipt_payload["result"], "committed")
        self.assertEqual(receipt_payload["promotion_scope"], "formal-pack")
        self.assertTrue(receipt_payload["formal_pack_published"])
        self.assertTrue((self.output / "tech-pack" / "repository-overview.md").is_file())
        self.assertEqual(
            receipt_payload["repository_register_artifact_schema_version"], "1"
        )
        self.assertEqual(
            receipt_payload["validator_domain_statuses"],
            {
                "dependency": "valid",
                "failure": "valid",
                "http": "valid",
                "markdown": "valid",
                "markdown-fragment": "valid",
            },
        )
        self.assertEqual(receipt_payload["primary_error_count"], 0)
        self.assertEqual(receipt_payload["skipped_group_count"], 0)

    def test_synthesis_commit_rejects_register_schema_drift(self) -> None:
        transaction, candidate = self.begin("inventory")
        (candidate / ".work" / "evidence-index.json").write_text(
            '{"artifact_type":"evidence-index","artifact_schema_version":"1"}\n',
            encoding="utf-8",
        )
        self.run_cmd("commit", "--output", str(self.output), "--transaction", transaction)

        tracing, _candidate = self.begin("tracing")
        self.run_cmd("commit", "--output", str(self.output), "--transaction", tracing)

        synthesis, candidate = self.begin("synthesis")
        executor = load_executor_module()
        register = candidate / ".work" / "repository-register.md"
        register.write_text(
            register.read_text(encoding="utf-8").replace(
                "| Dependency ID | Logical identity |",
                "| Dependency Identifier | Logical identity |",
                1,
            ),
            encoding="utf-8",
        )
        synthesis_text = "# Repository synthesis\n\n" + "\n\n".join(
            f"## {heading}" for heading in sorted(executor.SYNTHESIS_HEADINGS)
        ) + "\n"
        (candidate / ".work" / "repository-synthesis.md").write_text(
            synthesis_text,
            encoding="utf-8",
        )
        result = self.run_cmd(
            "commit",
            "--output",
            str(self.output),
            "--transaction",
            synthesis,
            "--semantic-result",
            "complete",
            expected=1,
        )
        payload = json.loads(result.stdout)
        self.assertIn("Register Schema", " ".join(payload["errors"]))
        formal = (self.output / ".work" / "analysis-state.yaml").read_text(encoding="utf-8")
        self.assertIn('current_stage: "synthesis"', formal)

    def test_archive_helper_detects_checksum_complete_tree(self) -> None:
        module = load_executor_module()
        source = self.root / "source"
        candidate = self.root / "candidate"
        (source / "ba-pack" / "behaviors").mkdir(parents=True)
        (source / "ba-pack" / "behaviors" / "a.md").write_text("a", encoding="utf-8")
        candidate.mkdir()
        archive = module.archive_legacy_ba(source, candidate, "test-tx")
        self.assertIsNotNone(archive)
        manifest = json.loads((archive / "archive-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["summary"]["files"], 1)


if __name__ == "__main__":
    unittest.main()
