# Install In Claude Code

Prompt Optimizer ships as a skills-only Claude Code plugin. It does not install an MCP server, request credentials, or make network calls.

After the repository is public:

```text
/plugin marketplace add SpannDaMan/prompt-optimizer
/plugin install prompt-optimizer@prompt-optimizer
```

The skill is exposed under the plugin namespace. Start a new Claude Code session after installation so the current plugin snapshot is loaded.

## Local validation

From the repository root:

```bash
claude plugin validate .
claude plugin marketplace add .
```

The second command is for local testing only. Do not confuse a successful local install with acceptance into Anthropic's official marketplace.

## Optional command-line tool

The plugin skill can use the bundled `scripts/prompt_optimizer.py` file. Installing the repository as a Python package additionally provides the global `prompt-optimizer` command:

```bash
python -m pip install .
prompt-optimizer --version
```

See [SUPPORT.md](../SUPPORT.md) for the supported boundary.
