from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "prompt-optimizer"
MODULE_PATH = PLUGIN / "scripts" / "prompt_optimizer.py"
SPEC = importlib.util.spec_from_file_location("prompt_optimizer", MODULE_PATH)
assert SPEC and SPEC.loader
prompt_optimizer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prompt_optimizer
SPEC.loader.exec_module(prompt_optimizer)


class PromptOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prompt_path = PLUGIN / "examples" / "long-request.txt"
        cls.brief_path = PLUGIN / "examples" / "optimized-brief.json"
        cls.prompt = cls.prompt_path.read_text(encoding="utf-8")
        cls.brief = json.loads(cls.brief_path.read_text(encoding="utf-8"))

    def test_sentence_count_ignores_fenced_code_and_quotes(self) -> None:
        prompt = "One. Two.\n```\nFake. Fake.\n```\n> Quoted.\nThree. Four."
        self.assertEqual(prompt_optimizer.count_sentences(prompt), 4)

    def test_long_prompt_triggers_optimization(self) -> None:
        self.assertEqual(prompt_optimizer.expected_trigger_decision(self.prompt), "optimize")

    def test_explicit_skip_overrides_long_prompt(self) -> None:
        prompt = "Do not rewrite this. Keep it exact. It has four sentences. Use my prompt as-is."
        self.assertEqual(prompt_optimizer.expected_trigger_decision(prompt), "skip")

    def test_skip_phrase_in_ignored_or_incidental_content_does_not_bypass_compilation(self) -> None:
        prompts = {
            "fence": "One. Two. Three. Four.\n```\nDo not rewrite this.\n```",
            "blockquote": "One. Two. Three. Four.\n> Do not rewrite this.",
            "transcript": "One. Two. Three. Four.\nQuoted transcript:\nDo not rewrite this.\n",
            "inline_quote": 'One. Two. Three. Four. The example says "Do not rewrite this."',
            "incidental": "One. Two. Three. The phrase do not rewrite appears in the documentation. Four.",
        }
        for label, prompt in prompts.items():
            with self.subTest(label=label):
                self.assertEqual(prompt_optimizer.expected_trigger_decision(prompt), "optimize")
                scaffold = prompt_optimizer.scaffold_prompt(prompt, "codex")
                self.assertEqual(scaffold["status"], "draft")
                self.assertFalse(prompt_optimizer.validate_brief(prompt, scaffold).valid)
                with self.assertRaises(ValueError):
                    prompt_optimizer.render_brief(prompt, scaffold)

    def test_analysis_is_deterministic_and_model_free(self) -> None:
        first = prompt_optimizer.analyze_prompt(self.prompt)
        second = prompt_optimizer.analyze_prompt(self.prompt)
        self.assertEqual(first, second)
        self.assertIn("No model was called", first["boundary"])

    def test_scaffold_for_long_prompt_is_draft(self) -> None:
        scaffold = prompt_optimizer.scaffold_prompt(self.prompt, "codex")
        self.assertEqual(scaffold["status"], "draft")
        result = prompt_optimizer.validate_brief(self.prompt, scaffold)
        self.assertFalse(result.valid)
        self.assertIn("brief_not_ready", result.error_codes)

    def test_scaffold_for_short_prompt_is_ready_and_unchanged(self) -> None:
        prompt = "Fix this bug and run tests."
        scaffold = prompt_optimizer.scaffold_prompt(prompt, "codex")
        self.assertEqual(scaffold["status"], "ready")
        self.assertEqual(scaffold["compiled_prompt"]["text"], prompt)
        self.assertTrue(prompt_optimizer.validate_brief(prompt, scaffold).valid)

    def test_complete_example_validates(self) -> None:
        result = prompt_optimizer.validate_brief(self.prompt, self.brief)
        self.assertTrue(result.valid, result.errors)

    def test_render_returns_exact_compiled_prompt(self) -> None:
        rendered = prompt_optimizer.render_brief(self.prompt, self.brief)
        self.assertEqual(rendered, self.brief["compiled_prompt"]["text"])

    def test_trace_exposes_constraint_and_authority_custody(self) -> None:
        trace = prompt_optimizer.trace_brief(self.prompt, self.brief)
        self.assertTrue(trace["valid"])
        self.assertEqual(trace["constraint_count"], 2)
        self.assertEqual(trace["constraints"], self.brief["constraint_map"])
        self.assertEqual(trace["authorization_boundary"], self.brief["authorization_boundary"])
        self.assertIn("not semantic equivalence", trace["evidence_boundary"])

    def test_source_prompt_mismatch_fails_closed(self) -> None:
        result = prompt_optimizer.validate_brief(self.prompt + "Changed.", self.brief)
        self.assertFalse(result.valid)
        self.assertIn("original_prompt_mismatch", result.error_codes)
        self.assertIn("source_fingerprint_mismatch", result.error_codes)

    def test_unknown_top_level_field_is_rejected(self) -> None:
        brief = copy.deepcopy(self.brief)
        brief["surprise"] = True
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("unknown_top_level_fields", result.error_codes)

    def test_section_order_is_canonical(self) -> None:
        brief = copy.deepcopy(self.brief)
        brief["compiled_prompt"]["sections"][0], brief["compiled_prompt"]["sections"][1] = (
            brief["compiled_prompt"]["sections"][1],
            brief["compiled_prompt"]["sections"][0],
        )
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("section_order_invalid", result.error_codes)

    def test_compiled_text_must_match_exact_section_join(self) -> None:
        brief = copy.deepcopy(self.brief)
        brief["compiled_prompt"]["text"] += " Extra."
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("compiled_join_mismatch", result.error_codes)

    def test_constraint_map_must_cover_every_constraint_once(self) -> None:
        brief = copy.deepcopy(self.brief)
        brief["constraint_map"].pop()
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("constraint_mapping_missing", result.error_codes)

    def test_constraint_compiled_text_must_occur_once(self) -> None:
        brief = copy.deepcopy(self.brief)
        brief["constraint_map"][0]["compiled_text"] = "missing compiled constraint"
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("constraint_not_preserved_once", result.error_codes)

    def test_explicit_external_authority_requires_evidence(self) -> None:
        brief = copy.deepcopy(self.brief)
        brief["authorization_boundary"]["external_actions"] = "explicitly_authorized"
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("approval_evidence_missing", result.error_codes)

    def test_source_grounded_local_authority_validates(self) -> None:
        result = prompt_optimizer.validate_brief(self.prompt, self.brief)
        self.assertTrue(result.valid, result.errors)
        evidence = self.brief["authorization_boundary"]["approval_evidence"][0]
        self.assertEqual(evidence["boundary"], "local_reversible_execution")
        self.assertEqual(self.prompt.count(evidence["source_text"]), 1)
        self.assertEqual(evidence["source_text"].count(evidence["action_text"]), 1)

    def test_explicit_external_authority_accepts_exact_source_evidence(self) -> None:
        prompt = "Publish the report."
        brief = prompt_optimizer.scaffold_prompt(prompt, "codex")
        brief["authorization_boundary"]["external_actions"] = "explicitly_authorized"
        brief["authorization_boundary"]["approval_evidence"] = [
            {
                "id": "approval-1",
                "boundary": "external_actions",
                "action_text": "Publish",
                "source_text": "Publish the report.",
            }
        ]
        self.assertTrue(prompt_optimizer.validate_brief(prompt, brief).valid)

    def test_authority_evidence_fails_when_fabricated_or_detached(self) -> None:
        cases = []
        missing = copy.deepcopy(self.brief)
        missing["authorization_boundary"]["approval_evidence"] = []
        cases.append((missing, "approval_evidence_missing"))
        absent = copy.deepcopy(self.brief)
        absent["authorization_boundary"]["approval_evidence"][0]["source_text"] = "Fabricated authority."
        cases.append((absent, "approval_source_not_exact"))
        wrong_action = copy.deepcopy(self.brief)
        wrong_action["authorization_boundary"]["approval_evidence"][0]["action_text"] = "Publish"
        cases.append((wrong_action, "approval_action_not_linked"))
        wrong_boundary = copy.deepcopy(self.brief)
        wrong_boundary["authorization_boundary"]["approval_evidence"][0]["boundary"] = "external_actions"
        cases.append((wrong_boundary, "approval_evidence_missing"))
        for brief, code in cases:
            with self.subTest(code=code):
                self.assertIn(code, prompt_optimizer.validate_brief(self.prompt, brief).error_codes)

    def test_public_v1_shape_and_mapping_relationships_fail_closed(self) -> None:
        cases: list[tuple[str, dict, str]] = []
        non_string_candidate = copy.deepcopy(self.brief)
        non_string_candidate["candidate_constraints"].append(7)
        cases.append(("non-string candidate", non_string_candidate, "candidate_constraints_item_invalid"))
        duplicate_candidate = copy.deepcopy(self.brief)
        duplicate_candidate["candidate_constraints"].append(duplicate_candidate["candidate_constraints"][0])
        cases.append(("duplicate candidate", duplicate_candidate, "candidate_constraints_duplicate"))
        non_list_constraints = copy.deepcopy(self.brief)
        non_list_constraints["must_preserve_constraints"] = "not-a-list"
        cases.append(("non-list constraints", non_list_constraints, "must_preserve_constraints_invalid"))
        non_string_plan = copy.deepcopy(self.brief)
        non_string_plan["validation_plan"].append(9)
        cases.append(("non-string plan", non_string_plan, "validation_plan_item_invalid"))
        non_string_gated = copy.deepcopy(self.brief)
        non_string_gated["authorization_boundary"]["gated_actions"].append(4)
        cases.append(("non-string gated action", non_string_gated, "gated_actions_item_invalid"))
        wrong_evidence_shape = copy.deepcopy(self.brief)
        wrong_evidence_shape["authorization_boundary"]["approval_evidence"] = ["not-an-object"]
        cases.append(("wrong evidence shape", wrong_evidence_shape, "approval_evidence_record_invalid"))
        verbatim_changed = copy.deepcopy(self.brief)
        verbatim_changed["constraint_map"][0]["compiled_text"] = "Changed"
        cases.append(("changed verbatim", verbatim_changed, "verbatim_constraint_changed"))
        extra_map = copy.deepcopy(self.brief)
        extra = copy.deepcopy(extra_map["constraint_map"][0])
        extra["id"] = "constraint-extra"
        extra["source_text"] = "Run the relevant tests and report the exact validation results."
        extra["compiled_text"] = "Run the relevant tests and report the exact validation results."
        extra["compiled_section"] = "evidence_and_success"
        extra_map["constraint_map"].append(extra)
        cases.append(("extra map", extra_map, "constraint_mapping_extra"))
        for label, brief, code in cases:
            with self.subTest(label=label):
                result = prompt_optimizer.validate_brief(self.prompt, brief)
                self.assertFalse(result.valid)
                self.assertIn(code, result.error_codes)
                with self.assertRaises(ValueError):
                    prompt_optimizer.render_brief(self.prompt, brief)

    def test_skip_reason_and_skip_constraint_shapes_are_exact(self) -> None:
        prompt = "Fix this bug."
        wrong_reason = prompt_optimizer.scaffold_prompt(prompt, "codex")
        wrong_reason["skip_reason"] = "anything"
        self.assertIn("skip_reason_invalid", prompt_optimizer.validate_brief(prompt, wrong_reason).error_codes)
        non_string_reason = prompt_optimizer.scaffold_prompt(prompt, "codex")
        non_string_reason["skip_reason"] = 1
        result = prompt_optimizer.validate_brief(prompt, non_string_reason)
        self.assertIn("skip_reason_type", result.error_codes)
        non_list = prompt_optimizer.scaffold_prompt(prompt, "codex")
        non_list["constraint_map"] = {}
        result = prompt_optimizer.validate_brief(prompt, non_list)
        self.assertIn("constraint_map_invalid", result.error_codes)
        self.assertIn("skip_constraints_present", result.error_codes)

    def test_prompt_file_identity_preserves_bom_and_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixtures = {
                "lf": b"One.\nTwo.\n",
                "crlf": b"One.\r\nTwo.\r\n",
                "bom": b"\xef\xbb\xbfOne.\nTwo.\n",
            }
            identities = {}
            for name, data in fixtures.items():
                path = root / f"{name}.txt"
                path.write_bytes(data)
                prompt = prompt_optimizer.read_prompt(str(path))
                self.assertEqual(prompt.encode("utf-8"), data)
                identities[name] = prompt_optimizer.source_sha256(prompt)
            self.assertEqual(len(set(identities.values())), 3)

    def test_validation_errors_do_not_echo_source_constraint_text(self) -> None:
        marker = "SENSITIVE_MARKER_12345"
        brief = copy.deepcopy(self.brief)
        brief["constraint_map"][0]["source_text"] = marker
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertFalse(result.valid)
        self.assertNotIn(marker, json.dumps(result.to_payload()))
        with self.assertRaises(ValueError) as raised:
            prompt_optimizer.render_brief(self.prompt, brief)
        self.assertNotIn(marker, str(raised.exception))

    def test_reasoning_scaffolding_is_rejected(self) -> None:
        brief = copy.deepcopy(self.brief)
        section = brief["compiled_prompt"]["sections"][0]
        section["content"] += " Think step-by-step."
        included = [item["content"] for item in brief["compiled_prompt"]["sections"] if item["decision"] == "include"]
        brief["compiled_prompt"]["text"] = "\n\n".join(included)
        result = prompt_optimizer.validate_brief(self.prompt, brief)
        self.assertIn("reasoning_incantation", result.error_codes)

    def test_cli_analyze_json(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "analyze", "--prompt-file", str(self.prompt_path), "--format", "json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["trigger_decision"], "optimize")

    def test_cli_validate_complete_example(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "validate", "--prompt-file", str(self.prompt_path), "--brief-file", str(self.brief_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_cli_render_matches_example(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "render", "--prompt-file", str(self.prompt_path), "--brief-file", str(self.brief_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.rstrip("\n"), self.brief["compiled_prompt"]["text"])

    def test_cli_trace_returns_exact_constraint_map(self) -> None:
        result = subprocess.run(
            [sys.executable, str(MODULE_PATH), "trace", "--prompt-file", str(self.prompt_path), "--brief-file", str(self.brief_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["constraints"], self.brief["constraint_map"])
        self.assertEqual(payload["constraint_count"], 2)

    def test_cli_scaffold_writes_reviewable_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "draft.json"
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "scaffold", "--prompt-file", str(self.prompt_path), "--surface", "codex", "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "draft")

    def test_cli_scaffold_refuses_existing_or_symlink_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            existing = root / "existing.json"
            existing.write_text("preserve", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(MODULE_PATH), "scaffold", "--prompt-file", str(self.prompt_path), "--output", str(existing)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(existing.read_text(encoding="utf-8"), "preserve")
            self.assertNotIn(self.prompt, result.stderr)

            for label in ("valid-symlink", "broken-symlink"):
                destination = root / f"{label}.json"
                with self.subTest(destination=label), mock.patch.object(Path, "is_symlink", return_value=True):
                    with self.assertRaisesRegex(ValueError, "symlink"):
                        prompt_optimizer.write_new_output(destination, "do-not-write")
                self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
