# Prompt Optimizer Design System

## Machine-readable tokens

The canonical tokens live in `design.tokens.json`.

## Colors

- Deep navy `#06235D`: primary text and dark surface.
- Signal blue `#0183E0`: compiler/refinement core.
- Electric cyan `#09CEFC`: validated output signal.
- Cloud white `#F8FAFC`: light surface.
- Slate `#64748B`: secondary text.
- Pass green `#16A34A`, hold amber `#D97706`, and fail red `#DC2626`: state colors used sparingly.

## Typography

Use Inter, ui-sans-serif, or a system sans for product surfaces. Use a platform monospace stack for receipts and commands. Headings are compact and weight-forward; body copy stays readable at normal width.

## Layout

- Prefer one clear vertical story: source, compiler, receipt.
- Keep the first screen understandable without scrolling on a typical desktop repository view.
- Use generous whitespace and one dominant navy-to-blue-to-cyan voice-to-structure transition.
- Tables require short cells and explicit status labels.

## Shape and elevation

The core mark uses a stable microphone capsule, a thick waveform, and rounded horizontal prompt bars that form one continuous silhouette. Cards use 12-pixel radii and subtle borders; avoid glossy glass, heavy shadows, or neon bloom.

## Components

- Source card: deep navy border and the exact Agent Smith Palette mark.
- Compiler card: blue waveform transitioning into an aligned prompt stack.
- Receipt card: cyan structured-prompt bars with pass/hold/fail badge.
- Command block: dark surface, single copy target, no decorative chrome.

## Product line

Use `Compile clearly. Verify locally.` as the primary tagline. Do not use `Same intent` as an unqualified promise: deterministic checks prove source custody and mapped constraints, not full semantic equivalence.

## Accessibility

- Text contrast must meet WCAG AA.
- Status is never communicated by color alone.
- The mini mark must remain recognizable at 16, 24, 32, 64, and 128 pixels on light and dark surfaces.
- Screenshots must keep commands legible at 100 percent zoom.

## Asset authority

- Canonical source: `plugins/prompt-optimizer/assets/Prompt Optimizer Agent Smith Palette Master 210826.png`.
- Provenance and immutable hash: `plugins/prompt-optimizer/assets/Logo Generation Manifest 200826.json`.
- `icon.png`, `logo.png`, `logo-dark.png`, `screenshot1.png`, and `social-preview.png` are deterministic source-only derivatives using the full manifest-bound source.
- No SVG or local geometry reconstruction is a production source.

## Do

- Use the voice-or-text-to-structured-prompt metaphor and the selected deep navy, signal blue, and electric cyan palette.
- Keep icons geometric and readable without text.
- Show the no-model-call boundary near first-run examples.

## Do not

- Use brains, robots, generic magic wands, or fake AI sparkles.
- Suggest autonomous execution or guaranteed intelligence.
- Put paragraphs inside the mark, imply native speech recognition, or rely on gradients for legibility.
