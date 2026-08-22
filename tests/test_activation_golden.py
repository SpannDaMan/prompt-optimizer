from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate_activation_golden.py"
SPEC = importlib.util.spec_from_file_location("activation_golden_validator", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)
SUITE = next((ROOT / "evals").glob("*-activation-golden.json"))
REVISION = "a" * 64


class ActivationGoldenTests(unittest.TestCase):
    def test_frozen_suite_has_exact_class_counts(self) -> None:
        receipt = validator.evaluate_suite(validator.load_json(SUITE), REVISION)
        self.assertEqual(receipt["status"], "pass")
        self.assertEqual(receipt["case_count"], 30)
        self.assertEqual(receipt["class_counts"], {"direct": 10, "indirect": 10, "negative": 10})

    def test_suite_is_deterministic(self) -> None:
        payload = validator.load_json(SUITE)
        self.assertEqual(
            validator.evaluate_suite(payload, REVISION),
            validator.evaluate_suite(payload, REVISION),
        )

    def test_missing_case_fails_closed(self) -> None:
        payload = copy.deepcopy(validator.load_json(SUITE))
        payload["cases"].pop()
        with self.assertRaisesRegex(validator.GoldenError, "exactly 30"):
            validator.evaluate_suite(payload, REVISION)

    def test_output_never_overwrites(self) -> None:
        receipt = validator.evaluate_suite(validator.load_json(SUITE), REVISION)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "receipt.json"
            validator.write_new(output, receipt)
            with self.assertRaisesRegex(validator.GoldenError, "refusing to overwrite"):
                validator.write_new(output, receipt)


if __name__ == "__main__":
    unittest.main()
