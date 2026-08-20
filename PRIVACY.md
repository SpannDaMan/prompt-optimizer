# Privacy

Prompt Optimizer is a local, skills-only plugin and dependency-free command-line tool.

## Data handling

- It does not send prompts, prompt packets, traces, or validation results over the network.
- It does not include telemetry, analytics, advertising, hosted accounts, authentication, or tracking code.
- It does not require API keys or other credentials.
- Files are read from and written to paths selected by the user on the local machine.

Prompt packets intentionally contain the exact source prompt. They may therefore contain private repository context, business information, or other sensitive material. Keep packets local, redact them before sharing, and never place credentials or secrets in a prompt.

## Host products

When Prompt Optimizer is installed through ChatGPT, Codex, Claude Code, GitHub, or another host, that host's own privacy terms and telemetry settings still apply to the host product. Prompt Optimizer does not control or expand them.

## Contact

After publication, use the repository's security reporting path for private security concerns and GitHub Issues for non-sensitive privacy defects. See [SECURITY.md](SECURITY.md) and [SUPPORT.md](SUPPORT.md).
