# Support

Use GitHub Issues after publication for reproducible bugs and bounded feature requests.

Before opening an issue:

```bash
prompt-optimizer --version
python -B -m unittest discover -s tests -v
python tools/validate_release_candidate.py --json
```

Include the operating system, Python version, exact command, exit code, and a minimal redacted prompt/brief pair. Never post credentials, customer data, private repository content, or sensitive prompts.

Support covers the published CLI, schema, examples, and OpenAI/Codex and Claude skills-only plugin contracts. It does not cover provider behavior, model quality, hosted deployments, or third-party agent runtimes.

## Team rollout and private customization

After publication, use GitHub Discussions for non-sensitive questions about team rollout, private plugin catalogs, organization policy, or managed customization. Do not place credentials, private prompts, client data, or non-public repository details in a public discussion.

No support service, response time, private customization, or managed deployment is included with the MIT-licensed repository. Any paid or managed offering will require a separate scope and agreement.
