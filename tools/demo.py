#!/usr/bin/env python3
"""Run the committed Prompt Optimizer example with no dependencies or model calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "prompt-optimizer"
sys.path.insert(0, str(PLUGIN / "scripts"))

import prompt_optimizer  # noqa: E402


def main() -> int:
    """Validate and render the committed complete example."""

    prompt = (PLUGIN / "examples" / "long-request.txt").read_text(encoding="utf-8")
    brief = json.loads((PLUGIN / "examples" / "optimized-brief.json").read_text(encoding="utf-8"))
    try:
        rendered = prompt_optimizer.render_brief(prompt, brief)
    except ValueError as exc:
        print(f"demo failed: {exc}", file=sys.stderr)
        return 1
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
