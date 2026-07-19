#!/usr/bin/env python3
"""Mechanical contracts for typed lifecycle register and reader projections.

This module validates declared identities, controlled values, referential integrity,
and the projection of those declarations into Mermaid.  It deliberately does not
decide whether prose describes a real business state or whether code proves a
transition; those are AI semantic-review responsibilities.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from register_schema import RegisterSchema, section_value


DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "assets" / "lifecycle-model-schema.json"
LIFECYCLE_MODEL_VALIDATION_VERSION = "2"
NO_TRANSITION_SENTENCE = "No object state transition was established from repository evidence."
CODE_RE = re.compile(r"`([^`]+)`")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.S)
OBJECT_SECTION_RE = re.compile(r"^##\s+`?(OBJ-[0-9]+)`?\s+—\s+.+$", re.M)
STATE_DIAGRAM_RE = re.compile(
    r"<!--\s*lifecycle-state-diagram:\s*(OBJ-[0-9]+)\s*-->\s*"
    r"```mermaid\s*\n(?P<code>.*?)```",
    re.S,
)
PROCESSING_DIAGRAM_RE = re.compile(
    r"<!--\s*lifecycle-processing-diagram:\s*(OBJ-[0-9]+)\s*-->\s*"
    r"```mermaid\s*\n(?P<code>.*?)```",
    re.S,
)
STATE_DECLARATION_RE = re.compile(
    r'^\s*state\s+"(?P<id>STATE-[0-9]+)\s+—[^"\n]+"\s+as\s+(?P<alias>STATE_[0-9]+)\s*$',
    re.M,
)
TRANSITION_EDGE_RE = re.compile(
    r"^\s*(?P<from>STATE_[0-9]+)\s*-->\s*(?P<to>STATE_[0-9]+)\s*:"
    r"\s*(?P<id>TRANS-[0-9]+)\s+\[(?P<status>Confirmed|Inferred)\]\s*$",
    re.M,
)
SOURCE_RE = re.compile(
    r"`(?P<path>(?!https?://)[^`:\n]+\.[A-Za-z0-9_-]+):(?P<start>[0-9]+)"
    r"(?:-(?P<end>[0-9]+))?`"
)


class LifecycleSchemaError(RuntimeError):
    """The bundled lifecycle schema is unreadable or internally invalid."""


@dataclass
class LifecycleDomainResult:
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def load_lifecycle_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LifecycleSchemaError(f"cannot load lifecycle model schema {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("lifecycle_model_schema_version") != "2":
        raise LifecycleSchemaError("unsupported lifecycle model schema version")
    if payload.get("validation_version") != LIFECYCLE_MODEL_VALIDATION_VERSION:
        raise LifecycleSchemaError("lifecycle model validation version mismatch")
    required = {"ids", "state_bases", "evidence_statuses", "action_roles", "reader_tables", "diagram_contract"}
    missing = sorted(required - set(payload))
    if missing:
        raise LifecycleSchemaError("lifecycle model schema is missing: " + ", ".join(missing))
    try:
        for pattern in payload["ids"].values():
            re.compile(pattern)
    except (AttributeError, re.error) as exc:
        raise LifecycleSchemaError(f"invalid lifecycle ID pattern: {exc}") from exc
    return payload


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    content = section_value(text, heading)
    lines = content.splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.lstrip().startswith("|")), None)
    if header_index is None:
        return [], []
    header = _cells(lines[header_index])
    rows: list[list[str]] = []
    for line in lines[header_index + 2 :]:
        if not line.lstrip().startswith("|"):
            if rows:
                break
            continue
        rows.append(_cells(line))
    return header, rows


def _subsection(text: str, heading: str) -> str:
    match = re.search(
        rf"^###\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^###\s+|^##\s+|\Z)",
        text,
        re.M | re.S,
    )
    return match.group("body") if match else ""


def _subsection_table(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    content = _subsection(text, heading)
    lines = content.splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.lstrip().startswith("|")), None)
    if header_index is None:
        return [], []
    header = _cells(lines[header_index])
    rows: list[list[str]] = []
    for line in lines[header_index + 2 :]:
        if not line.lstrip().startswith("|"):
            if rows:
                break
            continue
        rows.append(_cells(line))
    return header, rows


def _code(cell: str) -> str:
    match = CODE_RE.search(cell)
    return (match.group(1) if match else cell).strip()


def _ids(cell: str, pattern: re.Pattern[str]) -> set[str]:
    candidates = re.findall(r"\b[A-Z][A-Z0-9-]*-[0-9]+\b", cell)
    return {candidate for candidate in candidates if pattern.fullmatch(candidate)}


def _frontmatter_value(text: str, key: str) -> str | None:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    value = re.search(rf"^{re.escape(key)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", match.group("body"), re.M)
    return value.group(1).strip() if value else None


def validate_lifecycle_register(
    register: Path,
    register_schema: RegisterSchema,
    lifecycle_schema: dict[str, Any] | None = None,
) -> LifecycleDomainResult:
    schema = lifecycle_schema or load_lifecycle_schema()
    if not register.is_file():
        return LifecycleDomainResult("invalid", errors=[f"repository register is missing: {register}"])
    text = register.read_text(encoding="utf-8")
    patterns = {name: re.compile(value) for name, value in schema["ids"].items()}
    statuses = set(schema["evidence_statuses"])
    bases = set(schema["state_bases"])
    roles = set(schema["action_roles"])
    errors: list[str] = []
    partial = False

    rows: dict[str, list[list[str]]] = {}
    for key in ("lifecycle_observations", "business_objects", "object_states", "processing_actions", "state_transitions"):
        contract = register_schema.tables[key]
        _header, table_rows = _table(text, contract.section)
        rows[key] = table_rows
        for row in table_rows:
            if len(row) != len(contract.headers):
                errors.append(f"{contract.section} row has the wrong number of columns")
                partial = True

    observations: dict[str, dict[str, Any]] = {}
    for row in rows["lifecycle_observations"]:
        if len(row) != len(register_schema.tables["lifecycle_observations"].headers):
            continue
        identifier = _code(row[0])
        if not patterns["observation"].fullmatch(identifier):
            errors.append(f"invalid Lifecycle Observation ID: {identifier or '<empty>'}")
            partial = True
            continue
        if identifier in observations:
            errors.append(f"duplicate Lifecycle Observation ID: {identifier}")
            partial = True
            continue
        if _code(row[7]) not in statuses:
            errors.append(f"Lifecycle Observation {identifier} has invalid Status: {_code(row[7])}")
        reconciliation = _code(row[9])
        refs = set()
        for kind in ("object", "state", "action", "transition"):
            refs.update(_ids(reconciliation, patterns[kind]))
        if reconciliation != "Unresolved" and not refs:
            errors.append(f"Lifecycle Observation {identifier} has invalid reconciliation: {reconciliation or '<empty>'}")
        observations[identifier] = {"reconciliation": reconciliation, "refs": refs}

    objects: dict[str, dict[str, Any]] = {}
    for row in rows["business_objects"]:
        if len(row) != len(register_schema.tables["business_objects"].headers):
            continue
        identifier = _code(row[0])
        if not patterns["object"].fullmatch(identifier):
            errors.append(f"invalid Object ID: {identifier or '<empty>'}")
            partial = True
            continue
        if identifier in objects:
            errors.append(f"duplicate Object ID: {identifier}")
            partial = True
            continue
        if _code(row[6]) not in statuses:
            errors.append(f"Object {identifier} has invalid Status: {_code(row[6])}")
        observation_refs = _ids(row[5], patterns["observation"])
        if not observation_refs:
            errors.append(f"Object {identifier} has no Lifecycle Observation IDs")
        objects[identifier] = {
            "observations": observation_refs,
            "status": _code(row[6]),
            "row": row,
        }

    states: dict[str, dict[str, Any]] = {}
    for row in rows["object_states"]:
        if len(row) != len(register_schema.tables["object_states"].headers):
            continue
        identifier = _code(row[0])
        object_id = _code(row[1])
        basis = _code(row[3])
        status = _code(row[6])
        if not patterns["state"].fullmatch(identifier):
            errors.append(f"invalid State ID: {identifier or '<empty>'}")
            partial = True
            continue
        if identifier in states:
            errors.append(f"duplicate State ID: {identifier}")
            partial = True
            continue
        if basis not in bases:
            errors.append(f"State {identifier} has invalid Basis: {basis or '<empty>'}")
        if status not in statuses:
            errors.append(f"State {identifier} has invalid Status: {status or '<empty>'}")
        if basis == "Derived" and status == "Confirmed":
            errors.append(f"Derived State cannot be Confirmed: {identifier}")
        states[identifier] = {"object_id": object_id, "basis": basis, "status": status, "row": row}

    actions: dict[str, dict[str, Any]] = {}
    for row in rows["processing_actions"]:
        if len(row) != len(register_schema.tables["processing_actions"].headers):
            continue
        identifier = _code(row[0])
        if not patterns["action"].fullmatch(identifier):
            errors.append(f"invalid Action ID: {identifier or '<empty>'}")
            partial = True
            continue
        if identifier in actions:
            errors.append(f"duplicate Action ID: {identifier}")
            partial = True
            continue
        object_ids = _ids(row[1], patterns["object"])
        role = _code(row[3])
        status = _code(row[8])
        if not object_ids:
            errors.append(f"Action {identifier} has no Object ID")
        if role not in roles:
            errors.append(f"Action {identifier} has invalid role: {role or '<empty>'}")
        if status not in statuses:
            errors.append(f"Action {identifier} has invalid Status: {status or '<empty>'}")
        actions[identifier] = {
            "object_ids": object_ids,
            "behavior_id": _code(row[2]),
            "transition_refs": _ids(row[6], patterns["transition"]),
            "role": role,
            "status": status,
            "row": row,
        }

    transitions: dict[str, dict[str, Any]] = {}
    for row in rows["state_transitions"]:
        if len(row) != len(register_schema.tables["state_transitions"].headers):
            continue
        identifier = _code(row[0])
        if not patterns["transition"].fullmatch(identifier):
            errors.append(f"invalid Transition ID: {identifier or '<empty>'}")
            partial = True
            continue
        if identifier in transitions:
            errors.append(f"duplicate Transition ID: {identifier}")
            partial = True
            continue
        status = _code(row[9])
        if status not in statuses:
            errors.append(f"Transition {identifier} has invalid Status: {status or '<empty>'}")
        transitions[identifier] = {
            "object_id": _code(row[1]),
            "from_state": _code(row[2]),
            "to_state": _code(row[3]),
            "behavior_id": _code(row[4]),
            "action_refs": _ids(row[5], patterns["action"]),
            "status": status,
            "row": row,
        }

    all_typed_ids = set(objects) | set(states) | set(actions) | set(transitions)
    if not partial:
        for state_id, state in states.items():
            if state["object_id"] not in objects:
                errors.append(f"State {state_id} references unknown Object: {state['object_id']}")
        for action_id, action in actions.items():
            for object_id in sorted(action["object_ids"] - set(objects)):
                errors.append(f"Action {action_id} references unknown Object: {object_id}")
            for transition_id in sorted(action["transition_refs"] - set(transitions)):
                errors.append(f"Action {action_id} references unknown Transition: {transition_id}")
        for transition_id, transition in transitions.items():
            object_id = transition["object_id"]
            if object_id not in objects:
                errors.append(f"Transition {transition_id} references unknown Object: {object_id}")
            endpoint_states = []
            for label in ("from_state", "to_state"):
                state_id = transition[label]
                state = states.get(state_id)
                if state is None:
                    errors.append(f"Transition {transition_id} references unknown State: {state_id}")
                else:
                    endpoint_states.append((state_id, state))
                    if state["object_id"] != object_id:
                        errors.append(
                            f"Transition {transition_id} crosses Object boundaries: "
                            f"{state_id} belongs to {state['object_id']}, not {object_id}"
                        )
            if not transition["action_refs"]:
                errors.append(f"Transition {transition_id} has no causing Action ID")
            for action_id in sorted(transition["action_refs"]):
                action = actions.get(action_id)
                if action is None:
                    errors.append(f"Transition {transition_id} references unknown Action: {action_id}")
                elif object_id not in action["object_ids"]:
                    errors.append(f"Transition {transition_id} uses Action {action_id} from another Object")
                elif transition_id not in action["transition_refs"]:
                    errors.append(f"Transition {transition_id} is missing from causing Action {action_id} backlinks")
        for action_id, action in actions.items():
            for transition_id in action["transition_refs"]:
                transition = transitions.get(transition_id)
                if transition is not None and action_id not in transition["action_refs"]:
                    errors.append(f"Action {action_id} is missing from Transition {transition_id} causing actions")
        for observation_id, observation in observations.items():
            for identifier in sorted(observation["refs"] - all_typed_ids):
                errors.append(f"Lifecycle Observation {observation_id} references unknown typed record: {identifier}")
        for object_id, item in objects.items():
            for observation_id in sorted(item["observations"] - set(observations)):
                errors.append(f"Object {object_id} references unknown Lifecycle Observation: {observation_id}")

    return LifecycleDomainResult(
        "partial" if partial else "valid",
        {
            "observations": observations,
            "objects": objects,
            "states": states,
            "actions": actions,
            "transitions": transitions,
        },
        errors,
    )


def _object_sections(text: str) -> dict[str, str]:
    matches = list(OBJECT_SECTION_RE.finditer(text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1)] = text[match.start() : end]
    return result


def _reader_ids(rows: list[list[str]], pattern: re.Pattern[str]) -> set[str]:
    return {_code(row[0]) for row in rows if row and pattern.fullmatch(_code(row[0]))}


def _validate_status_qualifier(cell: str, status: str, context: str, errors: list[str]) -> None:
    qualifiers = re.findall(r"\*\((Confirmed|Inferred|Unknown|Conflicting)\)\*", cell)
    if status == "Confirmed":
        if qualifiers:
            errors.append(f"{context} repeats a qualifier for Confirmed Reader content")
        return
    expected = f"*({status})*"
    if expected not in cell:
        errors.append(f"{context} must preserve Register status with {expected}")
    if any(item != status for item in qualifiers):
        errors.append(f"{context} has a qualifier that conflicts with Register status {status}")


def validate_lifecycle_document(
    document: Path,
    lifecycle: LifecycleDomainResult,
    repo: Path | None = None,
    lifecycle_schema: dict[str, Any] | None = None,
) -> list[str]:
    schema = lifecycle_schema or load_lifecycle_schema()
    data = lifecycle.data
    objects: dict[str, dict[str, Any]] = data.get("objects", {})
    states: dict[str, dict[str, Any]] = data.get("states", {})
    actions: dict[str, dict[str, Any]] = data.get("actions", {})
    transitions: dict[str, dict[str, Any]] = data.get("transitions", {})
    errors: list[str] = []
    if not any((objects, states, actions, transitions)):
        if document.is_file():
            errors.append("data-lifecycle.md exists but the Register contains no typed lifecycle records")
        return errors
    if not document.is_file():
        return ["typed lifecycle records exist but tech-pack/data-lifecycle.md is missing"]
    text = document.read_text(encoding="utf-8")
    if _frontmatter_value(text, "artifact_type") != "data-lifecycle":
        errors.append("data-lifecycle.md has the wrong artifact_type")
    if _frontmatter_value(text, "artifact_schema_version") != "3":
        errors.append("data-lifecycle.md must use artifact_schema_version 3")

    object_header, object_rows = _table(text, "Object landscape")
    if object_header != schema["reader_tables"]["object_landscape"]:
        errors.append("Data Lifecycle Object landscape has the wrong table header")
    published_objects = _reader_ids(object_rows, re.compile(schema["ids"]["object"]))
    if published_objects != set(objects):
        errors.append(
            "Data Lifecycle Object landscape does not match Register Objects: "
            f"missing={sorted(set(objects) - published_objects)}, extra={sorted(published_objects - set(objects))}"
        )
    for row in object_rows:
        object_id = _code(row[0]) if row else ""
        if object_id in objects:
            _validate_status_qualifier(row[0], objects[object_id]["status"], f"Object {object_id}", errors)

    sections = _object_sections(text)
    if set(sections) != set(objects):
        errors.append(
            "Data Lifecycle Object sections do not match Register Objects: "
            f"missing={sorted(set(objects) - set(sections))}, extra={sorted(set(sections) - set(objects))}"
        )

    state_diagrams: dict[str, str] = {}
    for match in STATE_DIAGRAM_RE.finditer(text):
        object_id = match.group(1)
        if object_id in state_diagrams:
            errors.append(f"Data Lifecycle has duplicate State Diagrams for {object_id}")
        state_diagrams[object_id] = match.group("code")
    processing_diagrams: dict[str, str] = {}
    for match in PROCESSING_DIAGRAM_RE.finditer(text):
        object_id = match.group(1)
        if object_id in processing_diagrams:
            errors.append(f"Data Lifecycle has duplicate Processing Diagrams for {object_id}")
        processing_diagrams[object_id] = match.group("code")

    covered_actions: set[str] = set()
    for object_id, section in sections.items():
        if f'<a id="{object_id.lower()}"></a>' not in text:
            errors.append(f"Data Lifecycle Object section lacks stable anchor: {object_id}")
        object_states = {key for key, value in states.items() if value["object_id"] == object_id}
        object_actions = {key for key, value in actions.items() if object_id in value["object_ids"]}
        object_transitions = {key for key, value in transitions.items() if value["object_id"] == object_id}
        established = {
            key for key in object_transitions if transitions[key]["status"] in {"Confirmed", "Inferred"}
        }

        state_header, state_rows = _subsection_table(section, "State vocabulary")
        if state_header != schema["reader_tables"]["state_vocabulary"]:
            errors.append(f"Data Lifecycle {object_id} State vocabulary has the wrong table header")
        published_states = _reader_ids(state_rows, re.compile(schema["ids"]["state"]))
        if published_states != object_states:
            errors.append(f"Data Lifecycle {object_id} State vocabulary does not match Register States")
        for row in state_rows:
            state_id = _code(row[0]) if row else ""
            if state_id in states:
                _validate_status_qualifier(row[0], states[state_id]["status"], f"State {state_id}", errors)

        transition_header, transition_rows = _subsection_table(section, "State transitions")
        published_transitions = _reader_ids(transition_rows, re.compile(schema["ids"]["transition"]))
        if object_transitions:
            if transition_header != schema["reader_tables"]["state_transitions"]:
                errors.append(f"Data Lifecycle {object_id} State transitions has the wrong table header")
            if published_transitions != object_transitions:
                errors.append(f"Data Lifecycle {object_id} Transition table does not match Register Transitions")
            for transition_id in published_transitions:
                if f'id="{transition_id.lower()}"' not in section:
                    errors.append(f"Data Lifecycle Transition lacks stable anchor: {transition_id}")
            for row in transition_rows:
                transition_id = _code(row[0]) if row else ""
                if transition_id in transitions:
                    _validate_status_qualifier(
                        row[0], transitions[transition_id]["status"], f"Transition {transition_id}", errors
                    )
        elif transition_header or transition_rows:
            errors.append(f"Data Lifecycle {object_id} publishes a Transition table without Register Transitions")

        diagram = state_diagrams.get(object_id)
        if established and diagram is None:
            errors.append(f"Data Lifecycle {object_id} has established Transitions but no tagged State Diagram")
        if not established and diagram is not None:
            errors.append(f"Data Lifecycle {object_id} has no established Transition but publishes a State Diagram")
        if not established and NO_TRANSITION_SENTENCE not in section:
            errors.append(f"Data Lifecycle {object_id} must state that no object State Transition was established")
        if diagram is not None:
            declarations = list(STATE_DECLARATION_RE.finditer(diagram))
            aliases: dict[str, str] = {}
            for declaration in declarations:
                state_id = declaration.group("id")
                alias = declaration.group("alias")
                if alias != state_id.replace("-", "_"):
                    errors.append(f"State Diagram {object_id} alias does not match State ID: {state_id} -> {alias}")
                if state_id not in object_states:
                    errors.append(f"State Diagram {object_id} references a State from another or unknown Object: {state_id}")
                aliases[alias] = state_id
            edge_ids: set[str] = set()
            for line in diagram.splitlines():
                stripped = line.strip()
                if "-->" not in stripped or not re.search(r"\bSTATE_[0-9]+\b", stripped):
                    continue
                if TRANSITION_EDGE_RE.fullmatch(line) is None:
                    errors.append(
                        f"State Diagram {object_id} contains an edge without a valid registered Transition label: {stripped}"
                    )
            for edge in TRANSITION_EDGE_RE.finditer(diagram):
                transition_id = edge.group("id")
                edge_ids.add(transition_id)
                transition = transitions.get(transition_id)
                if transition is None:
                    errors.append(f"State Diagram {object_id} references unknown Transition: {transition_id}")
                    continue
                if transition["object_id"] != object_id:
                    errors.append(f"State Diagram {object_id} references Transition from another Object: {transition_id}")
                if transition["status"] not in {"Confirmed", "Inferred"}:
                    errors.append(f"State Diagram publishes non-established Transition: {transition_id}")
                if edge.group("status") != transition["status"]:
                    errors.append(f"State Diagram status does not match Transition {transition_id}")
                if aliases.get(edge.group("from")) != transition["from_state"] or aliases.get(edge.group("to")) != transition["to_state"]:
                    errors.append(f"State Diagram endpoints do not match Transition {transition_id}")
            if edge_ids != established:
                errors.append(f"State Diagram {object_id} edges do not match established Register Transitions")
            all_aliases = set(re.findall(r"\bSTATE_[0-9]+\b", diagram))
            undeclared = all_aliases - set(aliases)
            if undeclared:
                errors.append(f"State Diagram {object_id} uses undeclared State aliases: {sorted(undeclared)}")
            if re.search(r"\bACT[-_][0-9]+\b", diagram):
                errors.append(f"State Diagram {object_id} contains an Action identity")

        action_header, action_rows = _subsection_table(section, "Processing and data movement")
        if object_actions:
            if action_header != schema["reader_tables"]["processing_actions"]:
                errors.append(f"Data Lifecycle {object_id} Processing table has the wrong header")
            published_actions = _reader_ids(action_rows, re.compile(schema["ids"]["action"]))
            for action_id in published_actions:
                if action_id not in object_actions:
                    errors.append(f"Data Lifecycle {object_id} lists Action from another Object: {action_id}")
            covered_actions.update(published_actions)
            for row in action_rows:
                action_id = _code(row[0]) if row else ""
                if action_id in actions:
                    _validate_status_qualifier(row[0], actions[action_id]["status"], f"Action {action_id}", errors)
        elif action_header or action_rows:
            errors.append(f"Data Lifecycle {object_id} publishes Processing Actions absent from the Register")

        processing = processing_diagrams.get(object_id)
        if processing is not None:
            if re.search(r"\bSTATE[-_][0-9]+\b", processing):
                errors.append(f"Processing Diagram {object_id} contains a State identity")
            visible_actions = set(re.findall(r"\bACT-[0-9]+\b", processing))
            aliases = set(re.findall(r"\bACT_[0-9]+\b", processing))
            expected_aliases = {item.replace("-", "_") for item in visible_actions}
            if aliases - expected_aliases:
                errors.append(f"Processing Diagram {object_id} uses an Action alias without a matching visible Action ID")
            for action_id in visible_actions:
                if action_id not in object_actions:
                    errors.append(f"Processing Diagram {object_id} references unknown or unrelated Action: {action_id}")

    if covered_actions != set(actions):
        errors.append(
            "Data Lifecycle Processing tables do not cover Register Actions: "
            f"missing={sorted(set(actions) - covered_actions)}, extra={sorted(covered_actions - set(actions))}"
        )
    for object_id in set(state_diagrams) | set(processing_diagrams):
        if object_id not in objects:
            errors.append(f"Data Lifecycle diagram tag references unknown Object: {object_id}")
    return errors


def validate_behavior_lifecycle_projection(root: Path, lifecycle: LifecycleDomainResult) -> list[str]:
    errors: list[str] = []
    actions = lifecycle.data.get("actions", {})
    transitions = lifecycle.data.get("transitions", {})
    actions_by_behavior: dict[str, set[str]] = {}
    transitions_by_behavior: dict[str, set[str]] = {}
    for identifier, item in actions.items():
        actions_by_behavior.setdefault(item["behavior_id"], set()).add(identifier)
    for identifier, item in transitions.items():
        transitions_by_behavior.setdefault(item["behavior_id"], set()).add(identifier)

    behavior_root = root / "tech-pack" / "behaviors"
    for document in sorted(behavior_root.glob("*.md")) if behavior_root.is_dir() else []:
        text = document.read_text(encoding="utf-8")
        behavior_id = _frontmatter_value(text, "behavior_id")
        if not behavior_id:
            continue
        action_ids = set(re.findall(r"\bACT-[0-9]+\b", text))
        transition_ids = set(re.findall(r"\bTRANS-[0-9]+\b", text))
        unknown_actions = action_ids - set(actions)
        unknown_transitions = transition_ids - set(transitions)
        if unknown_actions:
            errors.append(f"Tech Behavior {behavior_id} references unknown Actions: {sorted(unknown_actions)}")
        if unknown_transitions:
            errors.append(f"Tech Behavior {behavior_id} references unknown Transitions: {sorted(unknown_transitions)}")
        expected_actions = actions_by_behavior.get(behavior_id, set())
        expected_transitions = transitions_by_behavior.get(behavior_id, set())
        if action_ids != expected_actions:
            errors.append(f"Tech Behavior {behavior_id} Action projection does not match the Register")
        if transition_ids != expected_transitions:
            errors.append(f"Tech Behavior {behavior_id} Transition projection does not match the Register")
        _action_header, action_rows = _table(text, "Data access and processing")
        for row in action_rows:
            action_id = _code(row[0]) if row else ""
            if action_id in actions:
                _validate_status_qualifier(
                    row[0], actions[action_id]["status"], f"Tech Behavior {behavior_id} Action {action_id}", errors
                )
        _transition_header, transition_rows = _table(text, "Object state transitions")
        for row in transition_rows:
            transition_id = _code(row[0]) if row else ""
            if transition_id in transitions:
                _validate_status_qualifier(
                    row[0],
                    transitions[transition_id]["status"],
                    f"Tech Behavior {behavior_id} Transition {transition_id}",
                    errors,
                )
        for transition_id in transition_ids & set(transitions):
            target = f"../data-lifecycle.md#{transition_id.lower()}"
            if f"]({target})" not in text:
                errors.append(f"Tech Behavior {behavior_id} does not link Transition anchor: {transition_id}")
    return errors
