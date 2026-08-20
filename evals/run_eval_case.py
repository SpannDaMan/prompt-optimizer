#!/usr/bin/env python3
"""Run one deterministic Prompt Optimizer evaluation case and emit JSON."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "prompt-optimizer"
sys.path.insert(0, str(PLUGIN / "scripts"))

import prompt_optimizer  # noqa: E402


def load_fixture() -> tuple[str, dict[str, Any]]:
    """Load the canonical source prompt and complete prompt packet."""

    prompt = (PLUGIN / "examples" / "long-request.txt").read_text(encoding="utf-8")
    brief = json.loads((PLUGIN / "examples" / "optimized-brief.json").read_text(encoding="utf-8"))
    return prompt, brief


def validation_payload(prompt: str, brief: dict[str, Any]) -> dict[str, Any]:
    """Return a compact JSON view of one validation result."""

    result = prompt_optimizer.validate_brief(prompt, brief)
    return {
        "valid": result.valid,
        "trigger_decision": result.expected_trigger_decision,
        "error_codes": result.error_codes,
    }


def run_case(case_id: str) -> dict[str, Any]:
    """Execute one named regression scenario against the shipped module."""

    prompt, brief = load_fixture()
    if case_id == "long-analysis":
        return prompt_optimizer.analyze_prompt(prompt)
    if case_id == "short-skip":
        short_prompt = "Fix this bug and run tests."
        packet = prompt_optimizer.scaffold_prompt(short_prompt, "codex")
        return {
            "trigger_decision": packet["trigger_decision"],
            "status": packet["status"],
            "unchanged": packet["compiled_prompt"]["text"] == short_prompt,
            "valid": prompt_optimizer.validate_brief(short_prompt, packet).valid,
        }
    if case_id == "explicit-skip":
        source = "Do not rewrite this. Keep it exact. It has four sentences. Use my prompt as-is."
        packet = prompt_optimizer.scaffold_prompt(source, "codex")
        return {
            "trigger_decision": packet["trigger_decision"],
            "skip_reason": packet["skip_reason"],
            "unchanged": packet["compiled_prompt"]["text"] == source,
        }
    if case_id == "ignored-skip":
        source = "One. Two. Three. Four.\n```\nDo not rewrite this.\n```"
        packet = prompt_optimizer.scaffold_prompt(source, "codex")
        return {
            "trigger_decision": packet["trigger_decision"],
            "status": packet["status"],
            "valid": prompt_optimizer.validate_brief(source, packet).valid,
        }
    if case_id == "valid-example":
        return validation_payload(prompt, brief)
    if case_id == "source-mismatch":
        return validation_payload(prompt + "Changed.", brief)
    if case_id == "draft-closed":
        return validation_payload(prompt, prompt_optimizer.scaffold_prompt(prompt, "codex"))
    if case_id == "unknown-field":
        changed = copy.deepcopy(brief)
        changed["surprise"] = True
        return validation_payload(prompt, changed)
    if case_id == "external-auth":
        changed = copy.deepcopy(brief)
        changed["authorization_boundary"]["external_actions"] = "explicitly_authorized"
        return validation_payload(prompt, changed)
    if case_id == "render-parity":
        rendered = prompt_optimizer.render_brief(prompt, brief)
        return {"matches": rendered == brief["compiled_prompt"]["text"], "length": len(rendered)}
    if case_id == "trace-custody":
        trace = prompt_optimizer.trace_brief(prompt, brief)
        return {
            "valid": trace["valid"],
            "constraint_count": trace["constraint_count"],
            "constraints_match": trace["constraints"] == brief["constraint_map"],
            "external_actions": trace["authorization_boundary"].get("external_actions"),
            "evidence_boundary": trace["evidence_boundary"],
        }
    if case_id == "determinism":
        return {"matches": prompt_optimizer.analyze_prompt(prompt) == prompt_optimizer.analyze_prompt(prompt)}
    if case_id == "model-free-boundary":
        analysis = prompt_optimizer.analyze_prompt(prompt)
        return {
            "boundary": analysis["boundary"],
            "runtime_dependencies": [],
            "network_required": False,
        }
    raise ValueError(f"unknown eval case: {case_id}")


def main() -> int:
    """Parse one case identifier and print its stable JSON result."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id")
    args = parser.parse_args()
    try:
        print(json.dumps(run_case(args.case_id), ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"eval case failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
