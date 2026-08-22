from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


CASE_FIELDS = {
    "id",
    "class",
    "prompt",
    "expected_activation",
    "expected_behavior",
    "prohibited_behavior",
    "evidence_oracle",
}
EXPECTED_COUNTS = {"direct": 10, "indirect": 10, "negative": 10}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GoldenError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GoldenError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError, GoldenError) as exc:
        raise GoldenError(f"cannot read golden suite {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GoldenError("golden suite must be a JSON object")
    return payload


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GoldenError(f"{label} must be a non-empty string")
    return value.strip()


def evaluate_suite(payload: dict[str, Any], product_revision: str) -> dict[str, Any]:
    if set(payload) != {"schema_version", "suite_id", "plugin", "cases", "claim_boundary"}:
        raise GoldenError("golden suite fields are invalid")
    if payload.get("schema_version") != "1.0":
        raise GoldenError("golden suite schema_version must be 1.0")
    suite_id = require_text(payload.get("suite_id"), "suite_id")
    plugin = require_text(payload.get("plugin"), "plugin")
    claim_boundary = require_text(payload.get("claim_boundary"), "claim_boundary")
    if not SHA256_RE.fullmatch(product_revision):
        raise GoldenError("--product-revision must be a lowercase SHA-256 digest")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 30:
        raise GoldenError("golden suite must contain exactly 30 cases")

    ids: set[str] = set()
    prompts: set[str] = set()
    counts = {name: 0 for name in EXPECTED_COUNTS}
    results: list[dict[str, Any]] = []
    for index, raw in enumerate(cases):
        if not isinstance(raw, dict) or set(raw) != CASE_FIELDS:
            raise GoldenError(f"cases[{index}] fields are invalid")
        case_id = require_text(raw.get("id"), f"cases[{index}].id")
        case_class = require_text(raw.get("class"), f"cases[{index}].class")
        prompt = require_text(raw.get("prompt"), f"cases[{index}].prompt")
        if case_id in ids:
            raise GoldenError(f"duplicate case id: {case_id}")
        if prompt.casefold() in prompts:
            raise GoldenError(f"duplicate case prompt: {case_id}")
        if case_class not in counts:
            raise GoldenError(f"cases[{index}].class is invalid")
        expected = raw.get("expected_activation")
        if not isinstance(expected, bool):
            raise GoldenError(f"cases[{index}].expected_activation must be boolean")
        contract_activation = case_class in {"direct", "indirect"}
        if expected is not contract_activation:
            raise GoldenError(f"{case_id} activation conflicts with its class")
        behavior = require_text(raw.get("expected_behavior"), f"cases[{index}].expected_behavior")
        prohibited = require_text(raw.get("prohibited_behavior"), f"cases[{index}].prohibited_behavior")
        oracle = require_text(raw.get("evidence_oracle"), f"cases[{index}].evidence_oracle")
        ids.add(case_id)
        prompts.add(prompt.casefold())
        counts[case_class] += 1
        results.append(
            {
                "id": case_id,
                "class": case_class,
                "expected_activation": expected,
                "contract_activation": contract_activation,
                "status": "pass",
                "expected_behavior_sha256": sha256_bytes(behavior.encode("utf-8")),
                "prohibited_behavior_sha256": sha256_bytes(prohibited.encode("utf-8")),
                "evidence_oracle_sha256": sha256_bytes(oracle.encode("utf-8")),
            }
        )
    if counts != EXPECTED_COUNTS:
        raise GoldenError(f"golden suite class counts must be {EXPECTED_COUNTS}")

    return {
        "schema_version": "1.0",
        "artifact": "Plugin Activation Golden Receipt",
        "suite_id": suite_id,
        "plugin": plugin,
        "product_revision_sha256": product_revision,
        "suite_sha256": sha256_bytes(canonical_bytes(payload)),
        "case_count": len(results),
        "class_counts": counts,
        "status": "pass",
        "results": results,
        "claim_boundary": claim_boundary,
    }


def write_new(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise GoldenError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a deterministic plugin activation golden suite.")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--product-revision", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipt = evaluate_suite(load_json(args.suite), args.product_revision)
        if args.output:
            write_new(args.output, receipt)
        if args.json:
            print(json.dumps(receipt, indent=2, ensure_ascii=False))
        else:
            print(f"PASS: {receipt['plugin']} activation golden suite ({receipt['case_count']} cases)")
        return 0
    except GoldenError as exc:
        print(f"activation-golden: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
