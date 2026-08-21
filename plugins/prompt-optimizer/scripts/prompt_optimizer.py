#!/usr/bin/env python3
"""Compile and validate constraint-safe prompt packets without calling a model."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VERSION = "0.1.2"
SCHEMA_VERSION = "1.0"
SECTION_IDS = (
    "outcome",
    "relevant_context",
    "must_preserve_constraints",
    "evidence_and_success",
    "output_contract",
    "task_shape_routing",
    "final_verification",
)
TARGET_SURFACES = {"codex", "chatgpt", "openai_api", "other", "unknown"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "status",
    "source_sha256",
    "original_prompt",
    "sentence_count",
    "trigger_decision",
    "skip_reason",
    "target_surface",
    "candidate_constraints",
    "compiled_prompt",
    "must_preserve_constraints",
    "constraint_map",
    "authorization_boundary",
    "validation_plan",
}
SKIP_DIRECTIVE_PATTERNS = (
    re.compile(r"^(?:please\s+)?(?:do not|don't)\s+(?:optimize|rewrite|redraft)\b", re.IGNORECASE),
    re.compile(r"^(?:please\s+)?use my prompt as(?:-|\s)is\b", re.IGNORECASE),
)
CONSTRAINT_HINTS = (
    "must ",
    "must not",
    "do not",
    "don't",
    "never ",
    "only ",
    "without ",
    "preserve ",
    "keep ",
    "remain ",
    "blocked",
    "require ",
)
PROHIBITED_COMPILED_PATTERNS = (
    ("chain_of_thought_request", re.compile(r"\b(?:show|reveal) (?:me )?(?:your )?chain of thought\b", re.IGNORECASE)),
    ("reasoning_incantation", re.compile(r"\bthink (?:harder|step[- ]by[- ]step)\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class ValidationResult:
    """Represent one deterministic prompt-packet validation result."""

    valid: bool
    source_sha256: str
    sentence_count: int
    expected_trigger_decision: str
    errors: list[str]
    error_codes: list[str]
    warnings: list[str]

    def to_payload(self) -> dict[str, Any]:
        """Return a stable JSON-serializable validation receipt."""

        return {
            "tool": "prompt-optimizer",
            "version": VERSION,
            "valid": self.valid,
            "source_sha256": self.source_sha256,
            "sentence_count": self.sentence_count,
            "expected_trigger_decision": self.expected_trigger_decision,
            "errors": self.errors,
            "error_codes": self.error_codes,
            "warnings": self.warnings,
        }


def normalize_text(value: Any) -> str:
    """Normalize whitespace and case for conservative comparison."""

    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def strip_ignored_blocks(prompt: str) -> str:
    """Remove fenced code and explicitly quoted transcript blocks before analysis."""

    kept: list[str] = []
    in_fence = False
    in_quote_block = False
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        lowered = line.casefold()
        if line.startswith("```") or line.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if lowered in {"quoted transcript:", "quote:", "transcript:"}:
            in_quote_block = True
            continue
        if in_quote_block:
            if not line:
                in_quote_block = False
            continue
        if line.startswith(">"):
            continue
        kept.append(raw_line)
    return "\n".join(kept)


def split_sentences(prompt: str) -> list[str]:
    """Split analyzable prompt text into conservative punctuation-delimited sentences."""

    compact = re.sub(r"\s+", " ", strip_ignored_blocks(prompt)).strip()
    if not compact:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]


def count_sentences(prompt: str) -> int:
    """Count prompt sentences after ignored blocks are removed."""

    return len(split_sentences(prompt))


def explicit_skip_requested(prompt: str) -> bool:
    """Return whether analyzable source text contains a direct skip directive."""

    return any(
        pattern.search(sentence.strip())
        for sentence in split_sentences(prompt)
        for pattern in SKIP_DIRECTIVE_PATTERNS
    )


def expected_trigger_decision(prompt: str) -> str:
    """Return optimize for prompts longer than three sentences unless explicitly skipped."""

    if explicit_skip_requested(prompt):
        return "skip"
    return "optimize" if count_sentences(prompt) > 3 else "skip"


def source_sha256(prompt: str) -> str:
    """Return the SHA-256 fingerprint of the exact UTF-8 source prompt."""

    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def candidate_constraints(prompt: str) -> list[str]:
    """Return conservative constraint candidates without treating them as final mappings."""

    candidates: list[str] = []
    for sentence in split_sentences(prompt):
        lowered = f" {normalize_text(sentence)} "
        if any(hint in lowered for hint in CONSTRAINT_HINTS):
            candidates.append(sentence)
    return candidates


def analyze_prompt(prompt: str) -> dict[str, Any]:
    """Return a deterministic trigger analysis without calling a model."""

    return {
        "tool": "prompt-optimizer",
        "version": VERSION,
        "source_sha256": source_sha256(prompt),
        "sentence_count": count_sentences(prompt),
        "explicit_skip": explicit_skip_requested(prompt),
        "trigger_decision": expected_trigger_decision(prompt),
        "candidate_constraints": candidate_constraints(prompt),
        "boundary": "Deterministic analysis only. No model was called and no prompt was executed.",
    }


def _empty_sections() -> list[dict[str, str]]:
    """Return the canonical seven-section draft scaffold."""

    return [
        {
            "id": section_id,
            "decision": "omit",
            "content": "",
            "reason": "Requires semantic compilation by the bundled skill.",
        }
        for section_id in SECTION_IDS
    ]


def scaffold_prompt(prompt: str, surface: str) -> dict[str, Any]:
    """Create a safe draft envelope or a complete skip envelope from the exact prompt."""

    if surface not in TARGET_SURFACES:
        raise ValueError(f"target surface must be one of {sorted(TARGET_SURFACES)}")
    decision = expected_trigger_decision(prompt)
    if decision == "skip":
        skip_reason = "explicit_skip" if explicit_skip_requested(prompt) else "three_or_fewer_sentences"
        status = "ready"
        compiled_prompt = {"text": prompt, "sections": []}
    else:
        skip_reason = ""
        status = "draft"
        compiled_prompt = {"text": "", "sections": _empty_sections()}
    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "source_sha256": source_sha256(prompt),
        "original_prompt": prompt,
        "sentence_count": count_sentences(prompt),
        "trigger_decision": decision,
        "skip_reason": skip_reason,
        "target_surface": surface,
        "candidate_constraints": candidate_constraints(prompt),
        "compiled_prompt": compiled_prompt,
        "must_preserve_constraints": [],
        "constraint_map": [],
        "authorization_boundary": {
            "local_reversible_execution": "not_authorized",
            "external_actions": "gated",
            "scope_expansion": "gated",
            "gated_actions": [],
            "approval_evidence": [],
        },
        "validation_plan": [],
    }


def _add_error(errors: list[str], codes: list[str], code: str, message: str) -> None:
    """Append one stable validation error and code."""

    errors.append(message)
    codes.append(code)


def _as_list(value: Any) -> list[Any]:
    """Return a list value or an empty list for non-lists."""

    return value if isinstance(value, list) else []


def _duplicates(values: list[Any]) -> list[str]:
    """Return normalized duplicate values from a list."""

    normalized = [normalize_text(value) for value in values if normalize_text(value)]
    return sorted({value for value in normalized if normalized.count(value) > 1})


def _validate_string_list(
    value: Any,
    field: str,
    errors: list[str],
    codes: list[str],
) -> list[str] | None:
    """Validate one JSON Schema string-array field without exposing its contents."""

    if not isinstance(value, list):
        _add_error(errors, codes, f"{field}_invalid", f"{field} must be a list")
        return None
    if any(not isinstance(item, str) for item in value):
        _add_error(errors, codes, f"{field}_item_invalid", f"{field} items must be strings")
        return None
    if len(value) != len(set(value)):
        _add_error(errors, codes, f"{field}_duplicate", f"{field} items must be unique")
    return value


def _validate_v1_shape(brief: dict[str, Any], errors: list[str], codes: list[str]) -> None:
    """Enforce the public v1 JSON types and uniqueness rules before relationships."""

    if not isinstance(brief.get("schema_version"), str):
        _add_error(errors, codes, "schema_version_type", "schema_version must be a string")
    if not isinstance(brief.get("status"), str):
        _add_error(errors, codes, "status_type", "status must be a string")
    fingerprint = brief.get("source_sha256")
    if not isinstance(fingerprint, str) or re.fullmatch(r"[a-f0-9]{64}", fingerprint) is None:
        _add_error(errors, codes, "source_sha256_shape", "source_sha256 must be 64 lowercase hexadecimal characters")
    if not isinstance(brief.get("original_prompt"), str):
        _add_error(errors, codes, "original_prompt_type", "original_prompt must be a string")
    sentence_count = brief.get("sentence_count")
    if isinstance(sentence_count, bool) or not isinstance(sentence_count, int) or sentence_count < 0:
        _add_error(errors, codes, "sentence_count_type", "sentence_count must be a non-negative integer")
    for field in ("trigger_decision", "skip_reason", "target_surface"):
        if not isinstance(brief.get(field), str):
            _add_error(errors, codes, f"{field}_type", f"{field} must be a string")
    for field in ("candidate_constraints", "must_preserve_constraints", "validation_plan"):
        _validate_string_list(brief.get(field), field, errors, codes)

    records = brief.get("constraint_map")
    if not isinstance(records, list):
        _add_error(errors, codes, "constraint_map_invalid", "constraint_map must be a list")
    else:
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                _add_error(errors, codes, "constraint_record_invalid", f"constraint_map[{index}] must be an object")
                continue
            required = {"id", "source_text", "disposition", "compiled_text", "compiled_section"}
            if set(record) != required:
                _add_error(errors, codes, "constraint_fields_invalid", f"constraint_map[{index}] must use the five canonical fields")
            for field in required:
                if not isinstance(record.get(field), str):
                    _add_error(errors, codes, "constraint_field_type", f"constraint_map[{index}].{field} must be a string")

    boundary = brief.get("authorization_boundary")
    if not isinstance(boundary, dict):
        _add_error(errors, codes, "authorization_invalid", "authorization_boundary must be an object")
        return
    required_boundary = {
        "local_reversible_execution",
        "external_actions",
        "scope_expansion",
        "gated_actions",
        "approval_evidence",
    }
    if set(boundary) != required_boundary:
        _add_error(errors, codes, "authorization_fields_invalid", "authorization_boundary must use the five canonical fields")
    for field in ("local_reversible_execution", "external_actions", "scope_expansion"):
        if not isinstance(boundary.get(field), str):
            _add_error(errors, codes, f"{field}_type", f"authorization_boundary.{field} must be a string")
    _validate_string_list(boundary.get("gated_actions"), "gated_actions", errors, codes)
    evidence = boundary.get("approval_evidence")
    if not isinstance(evidence, list):
        _add_error(errors, codes, "approval_evidence_invalid", "approval_evidence must be a list")
        return
    evidence_keys = {"id", "boundary", "action_text", "source_text"}
    seen_records: set[str] = set()
    for index, record in enumerate(evidence):
        if not isinstance(record, dict):
            _add_error(errors, codes, "approval_evidence_record_invalid", f"approval_evidence[{index}] must be an object")
            continue
        if set(record) != evidence_keys:
            _add_error(errors, codes, "approval_evidence_fields_invalid", f"approval_evidence[{index}] must use the four canonical fields")
        for field in evidence_keys:
            value = record.get(field)
            if not isinstance(value, str) or not value:
                _add_error(errors, codes, "approval_evidence_field_invalid", f"approval_evidence[{index}].{field} must be a non-empty string")
        identity = record.get("id")
        if isinstance(identity, str):
            if identity in seen_records:
                _add_error(errors, codes, "approval_evidence_id_duplicate", "approval_evidence ids must be unique")
            seen_records.add(identity)


def _validate_compiled_prompt(
    brief: dict[str, Any], errors: list[str], codes: list[str]
) -> dict[str, str]:
    """Validate canonical section shape and return included content by section id."""

    compiled = brief.get("compiled_prompt")
    if not isinstance(compiled, dict):
        _add_error(errors, codes, "compiled_prompt_invalid", "compiled_prompt must be an object")
        return {}
    if set(compiled) - {"text", "sections"}:
        _add_error(errors, codes, "compiled_prompt_unknown_field", "compiled_prompt contains unknown fields")
    text = compiled.get("text")
    sections = compiled.get("sections")
    if not isinstance(text, str):
        _add_error(errors, codes, "compiled_text_invalid", "compiled_prompt.text must be a string")
        text = ""
    if not isinstance(sections, list):
        _add_error(errors, codes, "compiled_sections_invalid", "compiled_prompt.sections must be a list")
        return {}
    decision = brief.get("trigger_decision")
    if decision == "skip":
        if text != brief.get("original_prompt"):
            _add_error(errors, codes, "skip_prompt_changed", "skip output must preserve the original prompt exactly")
        if sections:
            _add_error(errors, codes, "skip_sections_present", "skip output must not fabricate compiler sections")
        return {}

    ids = [str(item.get("id", "")) if isinstance(item, dict) else "" for item in sections]
    if ids != list(SECTION_IDS):
        _add_error(errors, codes, "section_order_invalid", "compiled sections must appear once in canonical order")
    included: list[str] = []
    content_by_id: dict[str, str] = {}
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            _add_error(errors, codes, "section_invalid", f"compiled section {index} must be an object")
            continue
        if set(section) != {"id", "decision", "content", "reason"}:
            _add_error(errors, codes, "section_fields_invalid", f"compiled section {index} must use the four canonical fields")
        section_id = str(section.get("id", ""))
        section_decision = section.get("decision")
        content = section.get("content")
        reason = section.get("reason")
        if not isinstance(content, str) or not isinstance(reason, str):
            _add_error(errors, codes, "section_text_invalid", f"compiled section {section_id or index} content and reason must be strings")
            continue
        if content != content.strip():
            _add_error(errors, codes, "section_whitespace", f"compiled section {section_id or index} has outer whitespace")
        if section_decision == "include":
            if not content:
                _add_error(errors, codes, "included_section_empty", f"compiled section {section_id or index} is included but empty")
            else:
                included.append(content)
                content_by_id[section_id] = content
            if reason:
                _add_error(errors, codes, "included_section_has_reason", f"included section {section_id or index} must use an empty reason")
        elif section_decision == "omit":
            if content:
                _add_error(errors, codes, "omitted_section_has_content", f"omitted section {section_id or index} contains content")
            if not reason.strip():
                _add_error(errors, codes, "omitted_section_reason_missing", f"omitted section {section_id or index} needs a reason")
            content_by_id[section_id] = ""
        else:
            _add_error(errors, codes, "section_decision_invalid", f"compiled section {section_id or index} decision must be include or omit")
    if sections and isinstance(sections[0], dict) and sections[0].get("decision") != "include":
        _add_error(errors, codes, "outcome_missing", "an optimized prompt must include the outcome section")
    expected_text = "\n\n".join(included)
    if text != expected_text:
        _add_error(errors, codes, "compiled_join_mismatch", "compiled_prompt.text must equal the ordered two-newline join of included sections")
    for code, pattern in PROHIBITED_COMPILED_PATTERNS:
        if pattern.search(text):
            _add_error(errors, codes, code, f"compiled prompt contains prohibited reasoning scaffolding: {code}")
    return content_by_id


def _validate_constraints(
    prompt: str,
    brief: dict[str, Any],
    content_by_id: dict[str, str],
    errors: list[str],
    codes: list[str],
) -> None:
    """Validate one-to-one source constraint custody and compiled placement."""

    constraints = brief.get("must_preserve_constraints")
    records = brief.get("constraint_map")
    if not isinstance(constraints, list):
        _add_error(errors, codes, "constraints_invalid", "must_preserve_constraints must be a list")
        return
    if not isinstance(records, list):
        _add_error(errors, codes, "constraint_map_invalid", "constraint_map must be a list")
        return
    for _duplicate in _duplicates(constraints):
        _add_error(errors, codes, "constraint_duplicate", "must-preserve constraints must be unique")
    source_records: dict[str, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            _add_error(errors, codes, "constraint_record_invalid", f"constraint_map[{index}] must be an object")
            continue
        if set(record) != {"id", "source_text", "disposition", "compiled_text", "compiled_section"}:
            _add_error(errors, codes, "constraint_fields_invalid", f"constraint_map[{index}] must use the five canonical fields")
        record_id = record.get("id", "")
        if not isinstance(record_id, str):
            continue
        record_id = record_id.strip()
        if not record_id:
            _add_error(errors, codes, "constraint_id_missing", f"constraint_map[{index}].id is required")
        elif record_id in seen_ids:
            _add_error(errors, codes, "constraint_id_duplicate", f"constraint_map[{index}].id is duplicated")
        else:
            seen_ids.add(record_id)
        source_text = record.get("source_text", "")
        if not isinstance(source_text, str):
            continue
        source_text = source_text.strip()
        source_records.setdefault(normalize_text(source_text), []).append(record)
        if not source_text or prompt.count(source_text) != 1:
            _add_error(errors, codes, "constraint_source_missing", f"constraint_map[{index}].source_text must occur exactly once in the original prompt")
        if record.get("disposition") not in {"verbatim", "semantic"}:
            _add_error(errors, codes, "constraint_disposition_invalid", f"constraint_map[{index}].disposition must be verbatim or semantic")
        compiled_text = record.get("compiled_text", "")
        compiled_section = record.get("compiled_section", "")
        if not isinstance(compiled_text, str) or not isinstance(compiled_section, str):
            continue
        compiled_text = compiled_text.strip()
        compiled_section = compiled_section.strip()
        if record.get("disposition") == "verbatim" and source_text != compiled_text:
            _add_error(errors, codes, "verbatim_constraint_changed", f"constraint_map[{index}] verbatim text must equal source_text")
        if compiled_section not in SECTION_IDS:
            _add_error(errors, codes, "constraint_section_invalid", f"constraint_map[{index}].compiled_section is invalid")
        elif not compiled_text or content_by_id.get(compiled_section, "").count(compiled_text) != 1:
            _add_error(errors, codes, "constraint_not_preserved_once", f"constraint_map[{index}].compiled_text must occur exactly once in its included section")
        if normalize_text(source_text) not in {normalize_text(item) for item in constraints if isinstance(item, str)}:
            _add_error(errors, codes, "constraint_mapping_extra", f"constraint_map[{index}] has no must-preserve constraint")
    for index, constraint in enumerate(constraints):
        if len(source_records.get(normalize_text(constraint), [])) != 1:
            _add_error(errors, codes, "constraint_mapping_missing", f"must_preserve_constraints[{index}] must map exactly once")


def _validate_authorization(prompt: str, brief: dict[str, Any], errors: list[str], codes: list[str]) -> None:
    """Validate local, external, and scope-expansion authority boundaries."""

    boundary = brief.get("authorization_boundary")
    if not isinstance(boundary, dict):
        _add_error(errors, codes, "authorization_invalid", "authorization_boundary must be an object")
        return
    required = {
        "local_reversible_execution",
        "external_actions",
        "scope_expansion",
        "gated_actions",
        "approval_evidence",
    }
    if set(boundary) != required:
        _add_error(errors, codes, "authorization_fields_invalid", "authorization_boundary must use the five canonical fields")
    if boundary.get("local_reversible_execution") not in {"allowed", "not_authorized"}:
        _add_error(errors, codes, "local_authorization_invalid", "local_reversible_execution is invalid")
    if boundary.get("external_actions") not in {"gated", "explicitly_authorized"}:
        _add_error(errors, codes, "external_authorization_invalid", "external_actions is invalid")
    if boundary.get("scope_expansion") not in {"gated", "explicitly_authorized"}:
        _add_error(errors, codes, "scope_authorization_invalid", "scope_expansion is invalid")
    gated_actions = boundary.get("gated_actions")
    evidence = boundary.get("approval_evidence")
    if not isinstance(gated_actions, list) or not isinstance(evidence, list):
        _add_error(errors, codes, "authorization_lists_invalid", "gated_actions and approval_evidence must be lists")
        return
    evidence_by_boundary: dict[str, int] = {}
    seen_ids: set[str] = set()
    for index, record in enumerate(evidence):
        if not isinstance(record, dict):
            continue
        identity = record.get("id")
        evidence_boundary = record.get("boundary")
        action_text = record.get("action_text")
        source_text = record.get("source_text")
        if not all(isinstance(item, str) and item for item in (identity, evidence_boundary, action_text, source_text)):
            continue
        if identity in seen_ids:
            continue
        seen_ids.add(identity)
        if evidence_boundary not in {"local_reversible_execution", "external_actions", "scope_expansion"}:
            _add_error(errors, codes, "approval_evidence_boundary_invalid", f"approval_evidence[{index}].boundary is invalid")
            continue
        if prompt.count(source_text) != 1:
            _add_error(errors, codes, "approval_source_not_exact", f"approval_evidence[{index}].source_text must occur exactly once in the original prompt")
            continue
        if source_text.count(action_text) != 1:
            _add_error(errors, codes, "approval_action_not_linked", f"approval_evidence[{index}].action_text must occur exactly once in source_text")
            continue
        evidence_by_boundary[evidence_boundary] = evidence_by_boundary.get(evidence_boundary, 0) + 1
    required_evidence = {
        "local_reversible_execution": boundary.get("local_reversible_execution") == "allowed",
        "external_actions": boundary.get("external_actions") == "explicitly_authorized",
        "scope_expansion": boundary.get("scope_expansion") == "explicitly_authorized",
    }
    for evidence_boundary, required_now in required_evidence.items():
        if required_now and evidence_by_boundary.get(evidence_boundary, 0) == 0:
            _add_error(errors, codes, "approval_evidence_missing", f"{evidence_boundary} requires source-grounded approval evidence")


def validate_brief(prompt: str, brief: dict[str, Any] | None) -> ValidationResult:
    """Validate one public Prompt Optimizer envelope and fail closed on ambiguity."""

    errors: list[str] = []
    codes: list[str] = []
    warnings: list[str] = []
    fingerprint = source_sha256(prompt)
    sentence_count = count_sentences(prompt)
    expected_decision = expected_trigger_decision(prompt)
    if not isinstance(brief, dict):
        _add_error(errors, codes, "brief_invalid", "brief must be a JSON object")
        return ValidationResult(False, fingerprint, sentence_count, expected_decision, errors, codes, warnings)

    unknown_fields = sorted(set(brief) - TOP_LEVEL_FIELDS)
    if unknown_fields:
        _add_error(errors, codes, "unknown_top_level_fields", f"unknown top-level fields: {', '.join(unknown_fields)}")
    missing_fields = sorted(TOP_LEVEL_FIELDS - set(brief))
    if missing_fields:
        _add_error(errors, codes, "missing_top_level_fields", f"missing top-level fields: {', '.join(missing_fields)}")
    _validate_v1_shape(brief, errors, codes)
    if brief.get("schema_version") != SCHEMA_VERSION:
        _add_error(errors, codes, "schema_version_invalid", f"schema_version must be {SCHEMA_VERSION}")
    if brief.get("original_prompt") != prompt:
        _add_error(errors, codes, "original_prompt_mismatch", "original_prompt must match the source prompt exactly")
    if brief.get("source_sha256") != fingerprint:
        _add_error(errors, codes, "source_fingerprint_mismatch", "source_sha256 does not match the exact source prompt")
    if brief.get("sentence_count") != sentence_count:
        _add_error(errors, codes, "sentence_count_mismatch", f"sentence_count must be {sentence_count}")
    if brief.get("trigger_decision") != expected_decision:
        _add_error(errors, codes, "trigger_decision_mismatch", f"trigger_decision must be {expected_decision}")
    if brief.get("target_surface") not in TARGET_SURFACES:
        _add_error(errors, codes, "target_surface_invalid", f"target_surface must be one of {sorted(TARGET_SURFACES)}")
    if not isinstance(brief.get("candidate_constraints"), list):
        _add_error(errors, codes, "candidate_constraints_invalid", "candidate_constraints must be a list")
    status = brief.get("status")
    if status not in {"draft", "ready"}:
        _add_error(errors, codes, "status_invalid", "status must be draft or ready")
    if status == "draft":
        _add_error(errors, codes, "brief_not_ready", "brief is a safe draft scaffold and requires semantic compilation before validation can pass")
        return ValidationResult(False, fingerprint, sentence_count, expected_decision, errors, codes, warnings)

    content_by_id = _validate_compiled_prompt(brief, errors, codes)
    if expected_decision == "skip":
        expected_skip_reason = "explicit_skip" if explicit_skip_requested(prompt) else "three_or_fewer_sentences"
        if brief.get("skip_reason") != expected_skip_reason:
            _add_error(errors, codes, "skip_reason_invalid", f"skip_reason must be {expected_skip_reason}")
        if brief.get("must_preserve_constraints") != [] or brief.get("constraint_map") != []:
            _add_error(errors, codes, "skip_constraints_present", "skip output must not fabricate constraint mappings")
    else:
        if brief.get("skip_reason") != "":
            _add_error(errors, codes, "unexpected_skip_reason", "optimized output must use an empty skip_reason")
        _validate_constraints(prompt, brief, content_by_id, errors, codes)
        plan = brief.get("validation_plan")
        if not isinstance(plan, list) or not plan or any(not str(item).strip() for item in plan):
            _add_error(errors, codes, "validation_plan_invalid", "optimized output requires a non-empty validation_plan")
    _validate_authorization(prompt, brief, errors, codes)
    return ValidationResult(not errors, fingerprint, sentence_count, expected_decision, errors, codes, warnings)


def render_brief(prompt: str, brief: dict[str, Any]) -> str:
    """Return compiled text only when the prompt packet passes validation."""

    result = validate_brief(prompt, brief)
    if not result.valid:
        raise ValueError("prompt packet is invalid: " + "; ".join(result.errors))
    compiled = brief["compiled_prompt"]
    return str(compiled["text"])


def trace_brief(prompt: str, brief: dict[str, Any]) -> dict[str, Any]:
    """Return inspectable constraint and authority custody for one valid packet."""

    result = validate_brief(prompt, brief)
    if not result.valid:
        raise ValueError("prompt packet is invalid: " + "; ".join(result.errors))
    records = brief.get("constraint_map", [])
    return {
        "tool": "prompt-optimizer",
        "version": VERSION,
        "valid": True,
        "source_sha256": result.source_sha256,
        "trigger_decision": result.expected_trigger_decision,
        "constraint_count": len(records) if isinstance(records, list) else 0,
        "constraints": records if isinstance(records, list) else [],
        "authorization_boundary": brief.get("authorization_boundary", {}),
        "validation_plan": brief.get("validation_plan", []),
        "privacy_notice": "This trace may include exact source constraint text. Keep it local and do not store secrets in prompt packets.",
        "evidence_boundary": "This proves packet custody and validation, not semantic equivalence or downstream model compliance.",
    }


def read_prompt(path: str) -> str:
    """Read strict UTF-8 bytes while preserving BOM and newline code points."""

    return Path(path).read_bytes().decode("utf-8")


def load_brief(path: str) -> dict[str, Any]:
    """Read one UTF-8 JSON prompt packet."""

    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("brief file must contain a JSON object")
    return payload


def write_new_output(path: Path, content: str) -> None:
    """Write one new UTF-8 file while refusing existing or symlink targets."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("output path is a symlink; refusing to write")
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ValueError("output path already exists; refusing to overwrite") from exc


def format_analysis(payload: dict[str, Any]) -> str:
    """Render a compact human-readable analysis receipt."""

    return "\n".join(
        (
            "Prompt Optimizer analysis",
            f"source_sha256: {payload['source_sha256']}",
            f"sentence_count: {payload['sentence_count']}",
            f"trigger_decision: {payload['trigger_decision']}",
            f"explicit_skip: {str(payload['explicit_skip']).lower()}",
            f"candidate_constraints: {len(payload['candidate_constraints'])}",
            f"boundary: {payload['boundary']}",
        )
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser."""

    parser = argparse.ArgumentParser(
        prog="prompt-optimizer",
        description="Deterministically inspect and validate prompt packets. The CLI never performs semantic rewriting or calls a model.",
        epilog="The bundled Codex skill performs semantic compilation. The CLI provides local custody, validation, trace, and fail-closed rendering.",
    )
    parser.add_argument("--version", action="version", version=f"prompt-optimizer {VERSION}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze trigger and constraint candidates.")
    analyze.add_argument("--prompt-file", required=True)
    analyze.add_argument("--format", choices=("text", "json"), default="text")

    scaffold = subparsers.add_parser("scaffold", help="Create a safe draft or complete skip envelope.")
    scaffold.add_argument("--prompt-file", required=True)
    scaffold.add_argument("--surface", choices=sorted(TARGET_SURFACES), default="codex")
    scaffold.add_argument("--output", default="-", help="Output JSON path, or - for stdout.")

    validate = subparsers.add_parser("validate", help="Validate a complete prompt packet.")
    validate.add_argument("--prompt-file", required=True)
    validate.add_argument("--brief-file", required=True)
    validate.add_argument("--format", choices=("text", "json"), default="text")

    trace = subparsers.add_parser("trace", help="Show constraint mappings and authority for a valid packet.")
    trace.add_argument("--prompt-file", required=True)
    trace.add_argument("--brief-file", required=True)

    render = subparsers.add_parser("render", help="Print compiled prompt text only after validation passes.")
    render.add_argument("--prompt-file", required=True)
    render.add_argument("--brief-file", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Prompt Optimizer command-line interface."""

    args = build_parser().parse_args(argv)
    try:
        prompt = read_prompt(args.prompt_file)
        if args.command == "analyze":
            payload = analyze_prompt(prompt)
            if args.format == "json":
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(format_analysis(payload))
            return 0
        if args.command == "scaffold":
            payload = scaffold_prompt(prompt, args.surface)
            rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
            if args.output == "-":
                sys.stdout.write(rendered)
            else:
                output_path = Path(args.output)
                write_new_output(output_path, rendered)
                print(f"WROTE: {output_path}")
            return 0
        brief = load_brief(args.brief_file)
        if args.command == "validate":
            result = validate_brief(prompt, brief)
            if args.format == "json":
                print(json.dumps(result.to_payload(), indent=2, ensure_ascii=False))
            elif result.valid:
                print("PASS: prompt packet is valid")
                print(f"source_sha256: {result.source_sha256}")
                print(f"trigger_decision: {result.expected_trigger_decision}")
            else:
                print("FAIL: prompt packet is invalid", file=sys.stderr)
                for error in result.errors:
                    print(f"- {error}", file=sys.stderr)
            return 0 if result.valid else 1
        if args.command == "trace":
            print(json.dumps(trace_brief(prompt, brief), indent=2, ensure_ascii=False))
            return 0
        sys.stdout.write(render_brief(prompt, brief))
        if not str(brief["compiled_prompt"]["text"]).endswith("\n"):
            sys.stdout.write("\n")
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"prompt-optimizer input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
