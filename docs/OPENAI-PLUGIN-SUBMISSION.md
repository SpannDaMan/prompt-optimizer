# OpenAI Plugin Submission Packet

Prompt Optimizer is prepared as a skills-only plugin. It has no MCP server, UI, authentication, credentials, network access, telemetry, or hosted data storage.

## Local package

- Plugin root: `plugins/prompt-optimizer`
- OpenAI/Codex manifest: `plugins/prompt-optimizer/.codex-plugin/plugin.json`
- Skill: `plugins/prompt-optimizer/skills/prompt-optimizer/SKILL.md`
- Scripts: `plugins/prompt-optimizer/scripts/`
- Public submission data: `submission/openai-plugin-submission.json`

## Submission prerequisites

Before submitting through the OpenAI Platform:

1. Confirm the locked Agent Smith Palette asset receipt and current release validation remain passing.
2. Publish the reviewed repository under `SpannDaMan/prompt-optimizer` with separate approval.
3. Confirm the public website, support, privacy, and terms URLs resolve.
4. Complete publisher identity verification in the owning OpenAI organization.
5. Upload the final skills-only archive and inspect the generated `.codex-plugin/plugin.json`.
6. Run all five positive and three negative cases in `submission/openai-plugin-submission.json`.
7. Submit for review only after a separate approval.

OpenAI review and directory publication are external actions. This repository does not treat a valid local package as review approval or public availability.
