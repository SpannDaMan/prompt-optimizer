#!/usr/bin/env python3
"""Validate the committed prompt packet against its JSON Schema without dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def json_identity(value: Any) -> str:
    """Return a stable JSON identity used for uniqueItems checks."""

    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Validate the JSON Schema keywords used by the public v1 contract."""

    errors: list[str] = []
    expected_type = schema.get("type")
    type_matches = {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
    }
    if expected_type in type_matches and not type_matches[expected_type]:
        return [f"{path}: expected {expected_type}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: does not match const")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: is outside enum")
    if isinstance(instance, str):
        if len(instance) < int(schema.get("minLength", 0)):
            errors.append(f"{path}: is shorter than minLength")
        pattern = schema.get("pattern")
        if isinstance(pattern, str) and re.search(pattern, instance) is None:
            errors.append(f"{path}: does not match pattern")
    if isinstance(instance, int) and not isinstance(instance, bool) and "minimum" in schema:
        if instance < int(schema["minimum"]):
            errors.append(f"{path}: is below minimum")
    if isinstance(instance, list):
        if schema.get("uniqueItems"):
            identities = [json_identity(item) for item in instance]
            if len(identities) != len(set(identities)):
                errors.append(f"{path}: items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate(item, item_schema, f"{path}[{index}]"))
    if isinstance(instance, dict):
        required = schema.get("required", [])
        if isinstance(required, list):
            for key in required:
                if key not in instance:
                    errors.append(f"{path}: missing required key {key}")
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            if schema.get("additionalProperties") is False:
                for key in sorted(set(instance) - set(properties)):
                    errors.append(f"{path}: additional key {key}")
            for key, child_schema in properties.items():
                if key in instance and isinstance(child_schema, dict):
                    errors.extend(validate(instance[key], child_schema, f"{path}.{key}"))
    return errors


def main() -> int:
    """Validate one instance and emit a bounded JSON receipt."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--instance", required=True)
    args = parser.parse_args()
    try:
        schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        instance = json.loads(Path(args.instance).read_text(encoding="utf-8"))
        errors = validate(instance, schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "errors": [str(exc)]}, indent=2))
        return 2
    print(json.dumps({"status": "pass" if not errors else "fail", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
