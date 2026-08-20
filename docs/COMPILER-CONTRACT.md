# Compiler Contract

Prompt Optimizer separates semantic compilation from deterministic validation.

## Trigger

Optimize a request longer than three relevant sentences unless an analyzable source sentence begins with a direct instruction not to optimize, rewrite, or redraft it, or to use it as-is. Fenced code, blockquotes, explicitly labeled quoted transcripts, inline quotations, and incidental discussion cannot activate the skip path.

Short or explicitly skipped UTF-8 prompts retain every decoded code point in the prompt packet and carry no fabricated compiler sections. The CLI reads strict UTF-8 bytes and preserves BOM and newline code points rather than applying BOM removal or newline canonicalization.

## Canonical sections

Every optimized packet contains the following section records once and in order:

1. `outcome`
2. `relevant_context`
3. `must_preserve_constraints`
4. `evidence_and_success`
5. `output_contract`
6. `task_shape_routing`
7. `final_verification`

Each record is either `include` with nonempty content and an empty reason, or `omit` with empty content and a concrete reason. Only `outcome` is universally required for optimized prompts. The compiled text is the exact two-newline join of included section content.

## Constraint custody

The `must_preserve_constraints` list stores exact source instructions whose loss would change scope, authority, safety, deliverables, or acceptance. Each item maps to exactly one `constraint_map` record. A mapping records the source text, verbatim or semantic disposition, compiled text, and target section. The compiled text must occur exactly once in that included section.

Constraint candidates from `scaffold` are hints, not authoritative custody decisions.

## Authorization

The packet separates:

- local reversible execution;
- external or consequential actions;
- material scope expansion.

Every local `allowed` state and every external or expansion state marked `explicitly_authorized` requires a structured approval-evidence record. Its `source_text` must occur exactly once in the source; its `action_text` must occur exactly once inside that source text; and its boundary must match the declared authority category. This proves source linkage, not that the compiler interpreted the permission correctly. The compiler may preserve authority already present in the source; it may not create it.

## Failure behavior

Draft or invalid packets cannot render. The caller should use the original prompt unchanged, correct the packet, or ask for a material missing decision. Validation is deterministic for the same prompt and brief.
