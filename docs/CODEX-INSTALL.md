# Codex Installation

## Local development

Use this lane for local development or when testing a checked-out release.

Install the Python CLI from the repository root:

```bash
python -m pip install .
prompt-optimizer --version
prompt-optimizer --help
```

The plugin package lives at `plugins/prompt-optimizer` and can be inspected or validated without a GitHub account.

## GitHub marketplace installation

After a separately approved public release, the intended commands are:

```bash
codex plugin marketplace add SpannDaMan/prompt-optimizer
codex plugin add prompt-optimizer@prompt-optimizer
```

Use a new Codex task after installation so the plugin snapshot is loaded.

## OpenAI Plugins Directory

The same skills-only package is also prepared for OpenAI's public Plugins Directory shared by supported ChatGPT and Codex surfaces. Directory submission is a reviewed external action and is separate from publishing the GitHub repository. See [OPENAI-PLUGIN-SUBMISSION.md](OPENAI-PLUGIN-SUBMISSION.md).
