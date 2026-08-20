# Release Evidence Contract

Prompt Optimizer binds generated release evidence to a non-self-referential product revision.

## Product revision digest

The product file set is every regular candidate file except:

- files below `validation/`;
- `.git/`, build, cache, bytecode, and packaging-residue paths;
- symlinks, which are forbidden by the release validator.

For each included file, sort by POSIX-style relative path and append this UTF-8 record:

```text
relative_path<TAB>byte_count<TAB>file_sha256<LF>
```

The SHA-256 of the complete record sequence is `product_revision_sha256`. Because generated receipts and reviewer ledgers live below `validation/`, writing a current receipt does not change the product revision it attests.

## Required binding

Package, eval, community-review, Codex-plugin, veteran-review, and composite receipts must record the exact current `product_revision_sha256`. The composite validator recomputes the digest, rejects stale receipts, and emits SHA-256 hashes for every accepted subreceipt.

This binding proves which product bytes a receipt names. It does not prove semantic equivalence, downstream model quality, hosted behavior, adoption, or market demand.
