# 30-Day Post-Release Maintainer Pilot

The pilot begins with the public `v0.1.0` release after the candidate passes every local gate and the maintainer records the publication decision. The earlier private-pilot-first requirement was explicitly overridden. The public repository may remain live during the pilot, but no new package-index upload, paid promotion, broader marketplace expansion, or feature-scope expansion is implied.

## Owner and participants

- Owner and final triage decision-maker: SpannDaMan.
- Default participant: the maintainer performing private local dogfooding.
- Optional participants: no more than five explicitly invited evaluators in addition to organic public users. Direct invitations require separate approval.
- Participant identities and contact details stay outside the repository. Public stars, forks, and downloads are discovery signals, not proof of product quality.

## Intake and privacy

Use one maintainer-controlled private issue or feedback log. Each entry records only a case ID, candidate product revision, environment, reproduction, expected/actual behavior, severity, disposition, and support minutes. Do not place source prompts, prompt packets, traces, secrets, credentials, customer data, participant identities, or private communications in the repository.

Participants must use synthetic or non-sensitive prompts. Any accidental sensitive-data report pauses intake until the material is removed from the working log and the handling path is reviewed.

## Cadence and change control

- Triage twice each week and record open P0-P3 counts, reproducibility, false-positive/false-negative reports, documentation confusion, and support minutes.
- Admit only the smallest change that fixes a reproduced compiler, custody, portability, privacy, or documentation defect.
- Every code or contract change creates a new product revision, reruns the full private validation gate, and is disclosed to active participants before further testing.
- New features, hosted services, model calls, telemetry, credentials, and scope expansion are deferred to a separate decision.

## Measures

Track:

- clean local install success and time to first passing demo;
- reproducible defects, severity, and time to first useful response;
- validation false positives and false negatives;
- repeated first-use or boundary questions;
- support minutes per participant and unresolved maintainer load;
- unsupported expectations such as hosted rewriting, model execution, or guaranteed quality.

These measures describe a bounded maintainer pilot. They do not establish adoption, demand, product-market fit, or model-performance improvement.

## Stop conditions

Pause the pilot immediately for a credible secret disclosure, prompt-content execution, network or credential access, validation bypass, ungrounded authorization, destructive local write, P0/P1 security issue, or unsustainable support burden. Resume only after a new revision closes the issue and passes the full private gate.

## Day-30 decision

- Continue private iteration when the boundary is understood, defects are reproducible, and maintainer load is sustainable.
- Narrow the product when repeated confusion points to one removable surface.
- Patch or temporarily mark the public release as affected when any P0-P2, privacy concern, misleading claim, or evidence gap emerges.
- Continue public maintenance only when the day-30 record shows a sustainable support and quality posture.
- Archive the candidate when the narrow contract cannot be maintained responsibly.

The pilot authorizes no additional publication, promotion, permission, credential, or spend action by itself.
