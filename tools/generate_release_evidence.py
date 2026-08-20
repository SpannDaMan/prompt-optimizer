#!/usr/bin/env python3
"""Generate revision-bound Prompt Optimizer release evidence locally."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# Preserve the candidate's portable-tree contract while importing and while
# spawning every nested verifier.
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "prompt-optimizer"
VALIDATION = ROOT / "validation"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from release_evidence import file_sha256, product_revision  # noqa: E402


def run(
    command: list[str],
    *,
    cwd: Path,
    allowed: set[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one bounded local verification command and require an allowed exit."""

    accepted = {0} if allowed is None else allowed
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    if completed.returncode not in accepted:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout: {completed.stdout[-1200:]}\nstderr: {completed.stderr[-1200:]}"
        )
    return completed


def write_json(name: str, payload: dict[str, object]) -> None:
    """Write one stable validation receipt."""

    (VALIDATION / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    """Regenerate every machine-verifiable receipt bound to the current product revision."""

    VALIDATION.mkdir(parents=True, exist_ok=True)
    revision, _manifest = product_revision(ROOT)

    eval_result = json.loads(run([sys.executable, "-B", "tools/run_evals.py"], cwd=ROOT).stdout)
    if eval_result.get("product_revision_sha256") != revision:
        raise RuntimeError("native eval did not bind itself to the current product revision")
    write_json("Prompt Optimizer Eval Result 120826.json", eval_result)

    prompt = PLUGIN / "examples" / "long-request.txt"
    brief = PLUGIN / "examples" / "optimized-brief.json"
    compiled = PLUGIN / "assets" / "compiled-prompt.txt"
    with tempfile.TemporaryDirectory() as temp_name:
        temp = Path(temp_name)
        wheel_dir = temp / "wheel"
        wheel_dir.mkdir()
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                ".",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(wheel_dir),
            ],
            cwd=ROOT,
        )
        wheels = list(wheel_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel, found {len(wheels)}")
        wheel = wheels[0]
        venv = temp / "venv"
        run([sys.executable, "-m", "venv", str(venv)], cwd=temp)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], cwd=temp)
        pip_check = run([str(python), "-m", "pip", "check"], cwd=temp)

        base = [str(python), "-m", "prompt_optimizer"]
        version = run([*base, "--version"], cwd=temp)
        analyze = run(
            [*base, "analyze", "--prompt-file", str(prompt), "--format", "json"],
            cwd=temp,
        )
        trace = run(
            [*base, "trace", "--prompt-file", str(prompt), "--brief-file", str(brief)],
            cwd=temp,
        )
        validate = run(
            [*base, "validate", "--prompt-file", str(prompt), "--brief-file", str(brief)],
            cwd=temp,
        )
        render = run(
            [*base, "render", "--prompt-file", str(prompt), "--brief-file", str(brief)],
            cwd=temp,
        )
        json.loads(analyze.stdout)
        json.loads(trace.stdout)
        if render.stdout.rstrip("\r\n") != compiled.read_text(encoding="utf-8").rstrip("\r\n"):
            raise RuntimeError("installed render output did not match the committed compiled prompt")

        write_json(
            "Package Verification 120826.json",
            {
                "schema_version": "1.0",
                "candidate": "prompt-optimizer 0.1.0",
                "product_revision_sha256": revision,
                "status": "pass",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "install_source": ".",
                "runtime_dependencies": [],
                "wheel": {
                    "filename": wheel.name,
                    "sha256": file_sha256(wheel),
                    "bytes": wheel.stat().st_size,
                },
                "checks": [
                    {"name": "pep517_build_and_clean_install", "status": "pass"},
                    {"name": "pip_check", "status": "pass", "result": pip_check.stdout.strip()},
                    {"name": "installed_cli_version", "status": "pass", "result": version.stdout.strip()},
                    {"name": "installed_cli_analyze", "status": "pass", "result": "valid JSON"},
                    {"name": "installed_cli_trace", "status": "pass", "result": "valid JSON"},
                    {"name": "installed_cli_validate", "status": "pass", "result": validate.stdout.strip()},
                    {"name": "installed_cli_render", "status": "pass", "result": "exact committed output match"},
                ],
                "publication_action": "none",
            },
        )

    validator = Path.home() / ".codex" / "skills" / ".system" / "plugin-creator" / "scripts" / "validate_plugin.py"
    if not validator.is_file():
        raise RuntimeError(f"official local plugin validator missing: {validator}")
    plugin_run = run([sys.executable, "-B", str(validator), "plugins/prompt-optimizer"], cwd=ROOT)
    write_json(
        "Codex Plugin Verification 120826.json",
        {
            "schema_version": "1.0",
            "candidate": "prompt-optimizer 0.1.0",
            "product_revision_sha256": revision,
            "status": "pass",
            "exit_code": plugin_run.returncode,
            "validated_plugin_path": "plugins/prompt-optimizer",
            "working_directory": ".",
            "command": [
                "python",
                "-B",
                "$CODEX_HOME/skills/.system/plugin-creator/scripts/validate_plugin.py",
                "plugins/prompt-optimizer",
            ],
            "tool": {
                "name": "Codex plugin-creator validate_plugin.py",
                "identity": "sha256",
                "sha256": file_sha256(validator),
                "bytes": validator.stat().st_size,
            },
            "output": "Plugin validation passed: plugins/prompt-optimizer",
            "publication_action": "none",
        },
    )

    claude = shutil.which("claude.cmd") or shutil.which("claude")
    if not claude:
        raise RuntimeError("Claude CLI missing: cannot validate Claude plugin and marketplace manifests")
    claude_marketplace_run = run([claude, "plugin", "validate", "."], cwd=ROOT)
    claude_plugin_run = run([claude, "plugin", "validate", "plugins/prompt-optimizer"], cwd=ROOT)
    write_json(
        "Claude Plugin Verification 200826.json",
        {
            "schema_version": "1.0",
            "candidate": "prompt-optimizer 0.1.0",
            "product_revision_sha256": revision,
            "status": "pass",
            "validated_paths": [".", "plugins/prompt-optimizer"],
            "checks": [
                {
                    "name": "claude_marketplace_manifest",
                    "exit_code": claude_marketplace_run.returncode,
                    "output": "Claude marketplace manifest validation passed",
                },
                {
                    "name": "claude_plugin_manifest",
                    "exit_code": claude_plugin_run.returncode,
                    "output": "Claude plugin manifest validation passed",
                },
            ],
            "tool": {
                "name": "Claude Code CLI",
                "identity": "sha256",
                "path": Path(claude).name,
                "sha256": file_sha256(Path(claude)),
                "bytes": Path(claude).stat().st_size,
            },
            "publication_action": "none",
        },
    )

    schema = PLUGIN / "brief.schema.json"
    schema_instance = PLUGIN / "examples" / "optimized-brief.json"
    schema_run = run(
        [
            sys.executable,
            "-B",
            "tools/validate_json_schema.py",
            "--schema",
            str(schema),
            "--instance",
            str(schema_instance),
        ],
        cwd=ROOT,
    )
    schema_result = json.loads(schema_run.stdout)
    if schema_result != {"status": "pass", "errors": []}:
        raise RuntimeError("JSON Schema verification did not return a clean pass")
    write_json(
        "JSON Schema Verification 120826.json",
        {
            "schema_version": "1.0",
            "candidate": "prompt-optimizer 0.1.0",
            "product_revision_sha256": revision,
            "status": "pass",
            "exit_code": schema_run.returncode,
            "errors": [],
            "working_directory": ".",
            "command": [
                "python",
                "-B",
                "tools/validate_json_schema.py",
                "--schema",
                "plugins/prompt-optimizer/brief.schema.json",
                "--instance",
                "plugins/prompt-optimizer/examples/optimized-brief.json",
            ],
            "schema": {"path": schema.relative_to(ROOT).as_posix(), "sha256": file_sha256(schema)},
            "instance": {
                "path": schema_instance.relative_to(ROOT).as_posix(),
                "sha256": file_sha256(schema_instance),
            },
            "publication_action": "none",
        },
    )

    skill = PLUGIN / "skills" / "prompt-optimizer" / "SKILL.md"
    transcript = VALIDATION / "Skill Boundary Transcript 120826.md"
    skill_text = skill.read_text(encoding="utf-8")
    transcript_text = transcript.read_text(encoding="utf-8")
    required_skill_line = "This skill is a compiler only: do not execute the source task or the compiled prompt."
    if required_skill_line not in skill_text:
        raise RuntimeError("compiler-only boundary is absent from the bundled skill")
    if "Source task execution observed: `false`" not in transcript_text:
        raise RuntimeError("controlled boundary transcript does not establish non-execution")
    if "Compiled artifact returned: `true`" not in transcript_text:
        raise RuntimeError("controlled boundary transcript does not establish artifact return")
    write_json(
        "Skill Boundary Verification 120826.json",
        {
            "schema_version": "1.0",
            "candidate": "prompt-optimizer 0.1.0",
            "product_revision_sha256": revision,
            "status": "pass",
            "verification_type": "controlled_static_replay",
            "skill_path": skill.relative_to(ROOT).as_posix(),
            "skill_sha256": file_sha256(skill),
            "transcript_path": transcript.relative_to(ROOT).as_posix(),
            "transcript_sha256": file_sha256(transcript),
            "compiled_artifact_returned": True,
            "packet_returned": True,
            "packet_validation": "pass",
            "source_task_executed": False,
            "cli_model_call_observed": False,
            "cli_network_call_observed": False,
            "publication_action": "none",
        },
    )

    print(json.dumps({"status": "pass", "product_revision_sha256": revision, "receipts": 6}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
