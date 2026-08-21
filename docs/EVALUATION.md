# Evaluation Guide

Prompt Optimizer validation is not a substitute for behavioral evaluation.

The public `v0.1.1` candidate makes no model-performance, conversion, or task-quality claim. Its current automated evidence covers deterministic custody and fail-closed packet behavior only.

Use the local validator for source custody, section structure, constraint placement, and authorization boundaries. Use representative model evals when a semantic rewrite could materially affect task success.

## Minimum semantic evaluation

1. Keep the original prompt as the baseline.
2. Select at least three representative tasks, including one edge case.
3. Run the original and compiled prompts against the same model/runtime configuration.
4. Grade task success, required evidence, constraint compliance, and material omissions.
5. Reject the rewrite when it improves style but loses a requirement or expands authority.

Avoid broad claims from a single example. Record model, configuration, dataset, grader, latency, token, and cost context when reporting a measured result.
