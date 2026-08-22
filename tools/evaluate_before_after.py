from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class FixtureError(ValueError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FixtureError(f"cannot read fixture suite: {exc}") from exc
    if not isinstance(value, dict):
        raise FixtureError("fixture suite must be an object")
    return value


def coverage(text: str, requirements: list[str]) -> dict[str, Any]:
    lowered = text.casefold()
    present = [item for item in requirements if item.casefold() in lowered]
    return {
        "present": present,
        "missing": [item for item in requirements if item not in present],
        "ratio": len(present) / len(requirements),
    }


def evaluate(path: Path, product_revision: str) -> dict[str, Any]:
    if not SHA256_RE.fullmatch(product_revision):
        raise FixtureError("--product-revision must be a lowercase SHA-256 digest")
    suite = load(path)
    if set(suite) != {"schema_version", "suite_id", "claim_boundary", "cases"} or suite.get("schema_version") != "1.0":
        raise FixtureError("fixture suite fields or identity are invalid")
    cases = suite.get("cases")
    if not isinstance(cases, list) or len(cases) < 3:
        raise FixtureError("fixture suite must contain at least three representative cases")
    results: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, case in enumerate(cases):
        fields = {"id", "source", "explicit_requirements", "assumptions_to_label", "prohibited_additions", "before_output", "after_output"}
        if not isinstance(case, dict) or set(case) != fields:
            raise FixtureError(f"cases[{index}] fields are invalid")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise FixtureError(f"cases[{index}].id is invalid")
        for key in ("source", "before_output", "after_output"):
            if not isinstance(case.get(key), str) or not case[key].strip():
                raise FixtureError(f"{case_id}.{key} must be non-empty text")
        for key in ("explicit_requirements", "assumptions_to_label", "prohibited_additions"):
            value = case.get(key)
            if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
                raise FixtureError(f"{case_id}.{key} must be a string list")
        requirements = case["explicit_requirements"]
        if not requirements:
            raise FixtureError(f"{case_id} must declare explicit requirements")
        before_coverage = coverage(case["before_output"], requirements)
        after_coverage = coverage(case["after_output"], requirements)
        after_lower = case["after_output"].casefold()
        assumption_labels = [item for item in case["assumptions_to_label"] if item.casefold() in after_lower]
        prohibited_before = [item for item in case["prohibited_additions"] if item.casefold() in case["before_output"].casefold()]
        prohibited_after = [item for item in case["prohibited_additions"] if item.casefold() in after_lower]
        after_valid = (
            after_coverage["ratio"] == 1.0
            and len(assumption_labels) == len(case["assumptions_to_label"])
            and not prohibited_after
        )
        results.append(
            {
                "id": case_id,
                "source_sha256": hashlib.sha256(case["source"].encode("utf-8")).hexdigest(),
                "before": {
                    "explicit_requirement_coverage": before_coverage,
                    "prohibited_additions_detected": prohibited_before,
                    "first_pass_fixture_valid": before_coverage["ratio"] == 1.0 and not prohibited_before,
                },
                "after": {
                    "explicit_requirement_coverage": after_coverage,
                    "assumption_labels_present": assumption_labels,
                    "prohibited_additions_detected": prohibited_after,
                    "scope_drift_detected": bool(prohibited_after),
                    "first_pass_fixture_valid": after_valid,
                },
                "status": "pass" if after_valid and after_coverage["ratio"] >= before_coverage["ratio"] else "fail",
            }
        )
        ids.add(case_id)
    status = "pass" if all(item["status"] == "pass" for item in results) else "fail"
    return {
        "schema_version": "1.0",
        "artifact": "Prompt Optimizer Representative Before/After Receipt",
        "suite_id": suite["suite_id"],
        "product_revision_sha256": product_revision,
        "suite_sha256": hashlib.sha256(json.dumps(suite, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest(),
        "case_count": len(results),
        "results": results,
        "status": status,
        "claim_boundary": suite["claim_boundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate bounded Prompt Optimizer before/after fixtures.")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--product-revision", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipt = evaluate(args.suite, args.product_revision)
        if args.json:
            print(json.dumps(receipt, indent=2, ensure_ascii=False))
        else:
            print(f"{receipt['status'].upper()}: {receipt['case_count']} representative cases")
        return 0 if receipt["status"] == "pass" else 1
    except FixtureError as exc:
        print(f"before-after: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
