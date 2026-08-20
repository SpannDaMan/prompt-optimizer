# Prompt Optimizer To Agent Smith Router

Prompt Optimizer is the first public layer because routing quality depends on the quality of the task description a router receives.

It does not choose a model or execute a route. It turns an unstructured request into a reviewable packet that can give a future router cleaner inputs:

| Prompt Optimizer output | Future routing use |
|---|---|
| Outcome | Classify the primary work type and required result. |
| Relevant context | Determine which tools, repositories, or providers are actually relevant. |
| Must-preserve constraints | Block routes that cannot honor scope, safety, privacy, or delivery requirements. |
| Authorization boundary | Separate local work from external, destructive, credentialed, or scope-expanding actions. |
| Evidence and success | Select verification and review lanes that can prove completion. |
| Task-shape routing | Decide whether the work is direct, staged, or safely parallelizable. |
| Final verification | Define what the router must require before returning `done`. |

The relationship is:

```text
raw request
    -> Prompt Optimizer
    -> validated prompt packet
    -> Agent Smith Router
    -> route decision and execution receipt
```

A clearer packet can reduce routing ambiguity, but it does not guarantee a better route. The Router must still use current capability, cost, risk, availability, and verification evidence.

Agent Smith Router is a planned follow-on public plugin. Prompt Optimizer has no runtime dependency on it.
