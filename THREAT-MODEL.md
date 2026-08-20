# Threat Model

## Assets to protect

- Exact source prompts and local files.
- Authorization boundaries and approval evidence.
- The integrity of compiled prompt text and receipts.
- Maintainer trust in examples, tests, and release artifacts.

## Trust boundaries

- Prompt and brief files are untrusted data.
- The local filesystem and Python interpreter are controlled by the user.
- The bundled skill can make semantic judgments but cannot expand the user's authority.
- The CLI validates structure and custody; it does not prove downstream model behavior.
- GitHub, package indexes, and hosted plugin marketplaces are outside the private candidate boundary.

## In-scope threats

### Source substitution

An attacker changes the prompt after a brief was compiled. Strict UTF-8 bytes, including BOM and newline code points, produce the source string and SHA-256 fingerprint; a mismatch fails validation.

### Constraint loss or duplication

A compiler drops, moves, or repeats a must-preserve instruction. Every custody entry must map one source constraint to compiled text that occurs exactly once in one included section.

### Authority laundering

A rewritten prompt turns a gated local, external, or scope-expanding action into an approved action. Every allowed or explicitly authorized state requires a structured record whose exact source and action text resolve once under the matching boundary. The check proves source linkage, not semantic correctness.

### Unsafe local output mutation

A scaffold destination already contains user data or redirects through a symlink. The CLI uses create-new semantics and refuses existing regular files, valid symlinks, and broken final-component symlinks.

### Receipt ambiguity

Unexpected fields or noncanonical section order create multiple interpretations. The public v1 contract rejects unknown top-level, compiled-section, constraint, and authorization fields.

### Prompt injection in source material

Pasted or retrieved instructions try to change the skill's role or validation policy. Source content remains data and cannot override system, developer, host, or user authority.

### Local data disclosure

Prompts may contain secrets or personal data. The tool does not transmit them, but generated files and shell history remain the user's responsibility. Use redacted fixtures for bug reports.

Complete packets and `trace` output retain exact source constraint text by design. They must be stored and deleted with the same care as the original prompt. The product does not claim that a hash-only or redacted packet provides equivalent custody evidence.

## Out of scope

- Guaranteeing that a model follows a valid prompt.
- Proving that an optimized prompt outperforms the original.
- Sandboxing the local Python interpreter or filesystem.
- Securing a modified fork that adds provider calls, templates, arbitrary code, or network services.
- Protecting prompt files that the user intentionally shares or commits.

## Security invariants

- No network or telemetry code.
- No credentials or provider configuration.
- No dynamic imports from prompt or brief content.
- No prompt execution.
- Fail closed on a draft or invalid packet.
- No render-without-validation bypass.
- No scaffold overwrite or final-component symlink write.
- Preserve the original prompt as the fallback.
