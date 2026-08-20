# Receipts

The prompt packet is the primary receipt. `brief.schema.json` documents its public v1 shape, while the CLI enforces semantic relationships that JSON Schema alone cannot express.

## Stable fields

- `source_sha256`: fingerprint of the exact strict UTF-8 bytes read by the CLI.
- `original_prompt`: the exact decoded code-point sequence, including any BOM character and original newline code points.
- `sentence_count`: count after fenced/quoted blocks are ignored.
- `trigger_decision`: `optimize` or `skip`.
- `status`: `draft` or `ready`.
- `compiled_prompt`: canonical section records and exact joined text.
- `must_preserve_constraints` and `constraint_map`: one-to-one custody.
- `authorization_boundary`: local, external, and expansion decisions.
- `validation_plan`: concrete checks for the resulting work.

## Determinism

Receipts intentionally omit timestamps. The same prompt and brief produce the same validation payload. Release records can add dates outside the core prompt packet.

The CLI reads prompt files as strict UTF-8 bytes, decodes them without BOM removal or newline canonicalization, and hashes the same code-point sequence re-encoded as UTF-8. Distinct BOM/no-BOM and CRLF/LF inputs therefore retain distinct identities.

Use `prompt-optimizer trace` to emit a review view containing each exact source constraint, its disposition, compiled text, destination section, authority boundary, and validation plan. The command accepts only a packet that already passes validation.

## Privacy

`original_prompt` is intentionally retained for exact custody, so the packet is as sensitive as the source prompt. Keep it local, do not place secrets in it, and apply your own deletion or retention policy. Hash-only storage is not equivalent to this contract because it cannot support the same source and constraint review.

## Limits

A valid receipt proves that the packet meets this repository's structural custody contract. It does not prove semantic equivalence, that a model was called, that the prompt was executed, that output quality improved, or that downstream instructions were followed.
