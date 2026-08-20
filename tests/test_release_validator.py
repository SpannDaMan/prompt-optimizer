"""Regression tests for the standalone release validator."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "tools" / "validate_release_candidate.py"

SPEC = importlib.util.spec_from_file_location("release_validator", VALIDATOR_PATH)
assert SPEC and SPEC.loader
release_validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_validator)


class ReleaseValidatorTests(unittest.TestCase):
    """Prove the release validator fails closed without hiding root causes."""

    def test_run_validation_executes_each_check_once(self) -> None:
        """Run every component once and preserve its specific failure category."""

        validator_names = (
            "validate_required_files",
            "validate_file_shape",
            "validate_text_safety",
            "validate_metadata",
            "validate_cross_platform_packaging",
            "validate_json_artifacts",
            "validate_logo_provenance",
            "validate_logo_selection_evidence",
            "validate_sample_analysis",
            "validate_sample_trace",
            "validate_demo",
            "validate_eval_evidence",
            "validate_package_evidence",
            "validate_plugin_evidence",
            "validate_claude_plugin_evidence",
            "validate_schema_evidence",
            "validate_skill_boundary",
            "validate_claims",
            "validate_private_pilot_contract",
            "validate_review_evidence",
        )
        with ExitStack() as stack:
            validators = {
                name: stack.enter_context(mock.patch.object(release_validator, name, return_value=[]))
                for name in validator_names
            }
            png_validator = stack.enter_context(
                mock.patch.object(
                    release_validator,
                    "validate_png_assets",
                    return_value=(["icon.png: expected 512x512, got 256x256"], {}),
                )
            )
            result = release_validator.run_validation()
        for validator in validators.values():
            validator.assert_called_once_with()
        png_validator.assert_called_once_with()
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["root"], ".")
        self.assertEqual(result["checks"]["png_assets"], "fail")
        self.assertEqual(result["errors"], ["icon.png: expected 512x512, got 256x256"])

    def test_dimension_only_png_failure_stays_specific(self) -> None:
        """Report a wrong dimension without manufacturing an alpha failure."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "icon.png"
            path.touch()
            opaque_row = bytes((0, 0, 0, 255)) * 256
            rows = [opaque_row] * 512
            with (
                mock.patch.object(release_validator, "ROOT", root),
                mock.patch.object(release_validator, "decode_png_rgba", return_value=(256, 512, rows)),
            ):
                errors = release_validator.validate_png(path, (512, 512, False))
        self.assertEqual(errors, ["icon.png: expected 512x512, got 256x512"])

    def test_missing_metadata_prerequisites_return_structured_error(self) -> None:
        """Return one stable metadata error when prerequisites are absent."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = root / "plugins" / "prompt-optimizer"
            with (
                mock.patch.object(release_validator, "ROOT", root),
                mock.patch.object(release_validator, "PLUGIN", plugin),
            ):
                errors = release_validator.validate_metadata()
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("metadata JSON failed:"), errors)

    def test_missing_logo_prerequisite_returns_structured_error(self) -> None:
        """Return one stable logo-provenance error when the canonical manifest is absent."""

        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = Path(temp_dir) / "plugins" / "prompt-optimizer"
            with mock.patch.object(release_validator, "PLUGIN", plugin):
                errors = release_validator.validate_logo_provenance()
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("logo generation manifest failed:"), errors)

    def test_cross_platform_packaging_requires_exact_funding_target(self) -> None:
        """Reject a funding file that expands beyond the approved publisher identity."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin = root / "plugins" / "prompt-optimizer"
            (root / ".github").mkdir(parents=True)
            (root / "docs").mkdir()
            (root / "submission").mkdir()
            (plugin / "skills" / "prompt-optimizer").mkdir(parents=True)
            (root / ".github" / "FUNDING.yml").write_text("github: [SomeoneElse]\n", encoding="utf-8")
            (root / "README.md").write_text("OpenAI/Codex Claude Code Agent Smith Router FUNDING.yml", encoding="utf-8")
            (root / "PRIVACY.md").write_text("does not send prompts; does not include telemetry", encoding="utf-8")
            (root / "TERMS.md").write_text("does not prove semantic equivalence", encoding="utf-8")
            (root / "docs" / "AGENT-SMITH-ROUTER-BRIDGE.md").write_text("does not guarantee a better route", encoding="utf-8")
            (root / "docs" / "LAUNCH-MEASUREMENT.md").write_text("Do not use stars alone", encoding="utf-8")
            (plugin / "skills" / "prompt-optimizer" / "SKILL.md").write_text(
                "python <plugin-root>/scripts/prompt_optimizer.py", encoding="utf-8"
            )
            (root / "submission" / "openai-plugin-submission.json").write_text(
                '{"submission_type":"skills_only","positive_tests":[1,2,3,4,5],"negative_tests":[1,2,3],"publication_action":"none"}',
                encoding="utf-8",
            )
            with (
                mock.patch.object(release_validator, "ROOT", root),
                mock.patch.object(release_validator, "PLUGIN", plugin),
            ):
                errors = release_validator.validate_cross_platform_packaging()
        self.assertIn("FUNDING.yml must contain only the approved SpannDaMan GitHub Sponsors target", errors)

    def test_maintainer_pilot_rejects_superseded_private_first_gate(self) -> None:
        """Reject public release docs that still claim the private pilot must finish first."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            required = "SpannDaMan no more than five private issue or feedback log triage twice change control stop conditions support minutes day-30 decision post-release public repository may remain live explicitly overridden"
            (root / "MAINTAINER-PILOT.md").write_text(
                required + " must finish before any public-release decision", encoding="utf-8"
            )
            for name in ("README.md", "PUBLICATION-GATE.md", "RELEASE-CHECKLIST.md"):
                (root / name).write_text("public release", encoding="utf-8")
            with mock.patch.object(release_validator, "ROOT", root):
                errors = release_validator.validate_private_pilot_contract()
        self.assertTrue(any("superseded pre-publication gate" in error for error in errors), errors)

    def test_missing_review_ledgers_return_structured_error(self) -> None:
        """Fail closed when either durable review ledger is unavailable."""

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch.object(release_validator, "ROOT", Path(temp_dir)):
                errors = release_validator.validate_review_evidence()
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("review evidence failed:"), errors)

    def test_product_revision_excludes_generated_validation_evidence(self) -> None:
        """Keep receipts outside the product identity while binding source changes."""

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "validation").mkdir()
            product = root / "README.md"
            receipt = root / "validation" / "receipt.json"
            product.write_text("product-v1", encoding="utf-8")
            receipt.write_text('{"revision":"first"}', encoding="utf-8")
            first, _manifest = release_validator.product_revision(root)
            receipt.write_text('{"revision":"second"}', encoding="utf-8")
            second, _manifest = release_validator.product_revision(root)
            product.write_text("product-v2", encoding="utf-8")
            third, _manifest = release_validator.product_revision(root)
        self.assertEqual(first, second)
        self.assertNotEqual(second, third)

    def test_stale_receipt_revision_is_rejected(self) -> None:
        """Reject a receipt retained after any product revision change."""

        with mock.patch.object(release_validator, "current_product_revision", return_value="b" * 64):
            self.assertEqual(
                release_validator.validate_revision_binding(
                    {"product_revision_sha256": "a" * 64}, "package verification"
                ),
                ["package verification product revision does not match the current candidate"],
            )

    def test_veteran_closeout_requires_matching_status_and_empty_blockers(self) -> None:
        """Accept the profile schema but keep hold and open blockers release-failing."""

        revision = "c" * 64
        community = {
            "review_type": "synthetic_github_community_pretest",
            "panel_size": 6,
            "status": "pass",
            "evidence_boundary": "This is a qualitative synthetic pretest only. No conversion, scale, or demand claims permitted.",
            "implemented_changes": ["one"],
            "product_revision_sha256": revision,
            "publication_action": "none",
        }
        status_pairs = {
            "hold": "blocked",
            "private_pilot_ready": "eligible_for_private_pilot",
            "public_release_ready_with_gates": "eligible_for_separate_publication_decision_after_gates",
        }
        for verdict, status in status_pairs.items():
            veteran = {
                "review_type": "final_private_release_review",
                "reviewer_type": "simulated_veteran_open_source_maintainer",
                "revision_identity": {"revision": revision},
                "product_revision_sha256": revision,
                "verdict": verdict,
                "status": status,
                "open_p0_p1_p2": {"P0": [], "P1": [], "P2": []},
                "open_p3": [],
                "finding_ids": [],
                "publication_action": "none",
            }
            with (
                self.subTest(verdict=verdict),
                mock.patch.object(release_validator, "load_json", side_effect=[community, veteran]),
                mock.patch.object(release_validator, "current_product_revision", return_value=revision),
            ):
                errors = release_validator.validate_review_evidence()
            self.assertNotIn("veteran maintainer verdict and status are incompatible", errors)
            if verdict == "hold":
                self.assertIn("veteran maintainer review still holds the private candidate", errors)
            else:
                self.assertEqual(errors, [])

        veteran["verdict"] = "private_pilot_ready"
        veteran["status"] = "blocked"
        veteran["open_p0_p1_p2"]["P1"] = ["PO-R001"]
        with (
            mock.patch.object(release_validator, "load_json", side_effect=[community, veteran]),
            mock.patch.object(release_validator, "current_product_revision", return_value=revision),
        ):
            errors = release_validator.validate_review_evidence()
        self.assertIn("veteran maintainer verdict and status are incompatible", errors)
        self.assertIn("veteran maintainer review must close all P0, P1, and P2 findings", errors)


if __name__ == "__main__":
    unittest.main()
