# Security Policy

## Supported version

Security fixes are evaluated for the latest released minor version. This private candidate is not yet a supported public release.

## Report a vulnerability

After publication, use GitHub private vulnerability reporting if it is enabled. Until then, contact the maintainer privately. Do not open a public issue containing exploit details, credentials, private prompts, or customer data.

Include the affected version, exact command, minimal reproduction, impact, and whether the issue requires untrusted prompt or brief files.

## Security boundary

Prompt Optimizer reads local text and JSON files with the permissions of the invoking user. It does not execute prompt content, call providers, open network connections, load plugins, evaluate templates, or run arbitrary code from a prompt packet.

Treat prompt and brief files as untrusted data. Review paths before running commands. The CLI intentionally rejects unknown receipt fields and renders only a packet that passes local validation. Validation cannot prove that a later model or agent will follow the prompt.

## Prompt-data custody

Complete prompt packets intentionally retain the exact source prompt so the SHA-256 and constraint mappings remain auditable. This means a saved packet is as sensitive as its source. Do not put passwords, API keys, private keys, access tokens, customer private data, or other secrets into a packet. Store packets only in an appropriate local location and delete them according to your own retention policy when they are no longer needed.

The CLI reads only the paths supplied by the invoking user and does not upload prompt text. `analyze` writes to standard output. `scaffold` writes a packet only when its `--output` destination is supplied (or emits it to standard output). It creates missing parent directories but refuses to overwrite an existing file or follow an existing final-component symlink. Shell redirection, logs, terminal history, backups, and version control remain the user's responsibility.

There is intentionally no validation-bypass flag. Rendering without a passing packet would defeat the custody contract.
