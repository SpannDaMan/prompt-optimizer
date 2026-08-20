#!/usr/bin/env python3
"""Run the repository's deterministic prompt-packet evaluation suite."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_evidence import product_revision  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object from a UTF-8 file."""

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def nested_value(payload: Any, field: str) -> Any:
    """Resolve a period-delimited field from nested JSON objects."""

    current = payload
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(field)
        current = current[part]
    return current


def evaluate_check(output: str, check: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one supported deterministic assertion against case output."""

    kind = str(check.get("type", ""))
    critical = bool(check.get("critical"))
    weight = float(check.get("weight", 1))
    detail = ""
    passed = False
    if kind == "must_include":
        value = str(check.get("value", ""))
        detail = f"must include `{value}`"
        passed = value in output
    elif kind == "must_not_include":
        value = str(check.get("value", ""))
        detail = f"must not include `{value}`"
        passed = value not in output
    elif kind == "regex":
        pattern = str(check.get("pattern", ""))
        detail = f"regex `{pattern}`"
        flags = re.IGNORECASE if check.get("ignore_case") else 0
        passed = re.search(pattern, output, flags) is not None
    elif kind == "json_field_equals":
        field = str(check.get("field", ""))
        expected = check.get("expected")
        detail = f"json field `{field}` equals `{expected}`"
        passed = nested_value(json.loads(output), field) == expected
    elif kind == "word_count_at_least":
        minimum = int(check.get("value", 0))
        detail = f"word count >= {minimum}"
        passed = len(output.split()) >= minimum
    elif kind == "word_count_at_most":
        maximum = int(check.get("value", 0))
        detail = f"word count <= {maximum}"
        passed = len(output.split()) <= maximum
    else:
        raise ValueError(f"unsupported check type: {kind}")
    return {
        "type": kind,
        "detail": detail,
        "weight": weight,
        "critical": critical,
        "pass": passed,
    }


def evaluate_case(case: dict[str, Any], runner: dict[str, Any]) -> dict[str, Any]:
    """Run one suite case and score all declared checks."""

    command = [str(item) for item in runner.get("command", [])]
    if not command:
        raise ValueError("runner.command must be a non-empty list")
    if command[0] in {"python", "python3", "py"}:
        command[0] = sys.executable
    command.extend(str(item) for item in case.get("runner_args", []))
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=float(runner.get("timeout_seconds", 30)),
    )
    runner_meta = {
        "command": ["python" if index == 0 else item for index, item in enumerate(command)],
        "exit_code": completed.returncode,
        "stderr": completed.stderr.strip(),
        "require_exit_zero": bool(runner.get("require_exit_zero", True)),
    }
    errors: list[str] = []
    if runner_meta["require_exit_zero"] and completed.returncode != 0:
        errors.append(f"runner exited with {completed.returncode}: {completed.stderr.strip() or 'no stderr'}")
    outcomes = [evaluate_check(completed.stdout, item) for item in case.get("checks", [])]
    total_weight = sum(float(item["weight"]) for item in outcomes) or 1.0
    passed_weight = sum(float(item["weight"]) for item in outcomes if item["pass"])
    critical_failures = [str(item["detail"]) for item in outcomes if item["critical"] and not item["pass"]]
    return {
        "id": str(case.get("id", "unnamed-case")),
        "pass": not errors and not critical_failures and passed_weight == total_weight,
        "score": round(passed_weight / total_weight, 4),
        "passed_weight": passed_weight,
        "total_weight": total_weight,
        "critical_failures": critical_failures,
        "errors": errors,
        "checks": outcomes,
        "runner": runner_meta,
        "output_excerpt": completed.stdout[:300],
    }


def evaluate_suite(suite: dict[str, Any]) -> dict[str, Any]:
    """Execute and score every case in one suite."""

    cases = suite.get("cases")
    runner = suite.get("runner")
    if not isinstance(cases, list) or not cases or not isinstance(runner, dict):
        raise ValueError("suite must contain cases and a runner object")
    results = [evaluate_case(case, runner) for case in cases if isinstance(case, dict)]
    total_weight = sum(float(item["total_weight"]) for item in results) or 1.0
    passed_weight = sum(float(item["passed_weight"]) for item in results)
    score = round(passed_weight / total_weight, 4)
    threshold = float(suite.get("pass_threshold", 1.0))
    critical = [str(item["id"]) for item in results if item["critical_failures"]]
    error_cases = [str(item["id"]) for item in results if item["errors"]]
    revision, _manifest = product_revision(ROOT)
    return {
        "suite_id": str(suite.get("suite_id", "prompt-optimizer-evals")),
        "product_revision_sha256": revision,
        "pass": score >= threshold and not critical and not error_cases,
        "pass_threshold": threshold,
        "score": score,
        "case_count": len(results),
        "critical_failure_cases": critical,
        "error_cases": error_cases,
        "cases": results,
    }


def main() -> int:
    """Run the selected suite and optionally save its JSON receipt."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="evals/prompt-optimizer-suite.json")
    parser.add_argument("--json-output", default="-")
    args = parser.parse_args()
    try:
        result = evaluate_suite(load_json(ROOT / args.suite))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f"prompt-optimizer eval error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.json_output == "-":
        sys.stdout.write(rendered)
    else:
        output = ROOT / args.json_output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"WROTE: {output.relative_to(ROOT)}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
