# Contributing

Thanks for helping make Prompt Optimizer clearer, safer, and more portable.

## Best first contribution

1. Pick one observable defect in source custody, constraint mapping, authorization validation, portability, or documentation.
2. Add the smallest failing test that proves it.
3. Make the smallest durable fix.
4. Run the full local validation commands.
5. Explain the behavior change and any compatibility risk in the pull request.

Avoid broad refactors without a demonstrated defect. Prompt Optimizer intentionally stays small and does not need a hosted service, model gateway, evaluation framework, MCP server, browser extension, or provider integration to fulfill its contract.

## Development

```bash
python -B -m unittest discover -s tests -v
python tools/demo.py
python tools/run_evals.py
python tools/validate_json_schema.py --schema plugins/prompt-optimizer/brief.schema.json --instance plugins/prompt-optimizer/examples/optimized-brief.json
python tools/validate_release_candidate.py --json
```

The supported runtime is Python 3.10 or later with no runtime dependencies.

## Pull requests

Include:

- the user-visible defect or improvement;
- before/after behavior;
- tests added or changed;
- commands run and results;
- any documentation, schema, or receipt compatibility impact.

Do not include credentials, private prompts, customer data, absolute local paths, generated caches, or third-party code without a compatible license and explicit provenance.
