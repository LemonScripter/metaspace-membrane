# ⚠️ DRAFT — NOT THE LICENSE IN EFFECT

**This is a working draft of a Business Source License (BSL 1.1) for review by IP counsel.
It is NOT in effect and grants NO rights.** The license that actually governs this repository
is [`LICENSE`](../LICENSE) (Proprietary — patent pending). This file exists only to prepare the
intended open-core wording so counsel can finalize it; nothing here is legal advice, and the
project's rights do not change until `LICENSE` itself is replaced after sign-off.

Rationale for the eventual move (recorded decision): BSL keeps the patent moat intact (unlike an
Apache-2.0 patent grant) while being source-available with a generous Additional Use Grant — free
for all non-competing use — and converting to a true open-source license on the Change Date.

---

## Business Source License 1.1 — proposed parameters

> The canonical BSL 1.1 legal text is published by MariaDB Corporation Ab. This file fills in
> only the four license parameters; counsel supplies/atttaches the full canonical text.

| Parameter | Proposed value (for counsel to confirm) |
|---|---|
| **Licensor** | Szőke László-Ferenc — MetaSpace.Bio Engine Project (admin@metaspace.bio) |
| **Licensed Work** | MetaSpace Membrane (the contents of this repository), each released version |
| **Additional Use Grant** | You may use, copy, modify, and redistribute the Licensed Work for **any purpose except a Competing Use**. A *Competing Use* is offering the Licensed Work (or a derivative) to third parties as a commercial product or hosted service whose primary value is a safety/guardrail/policy-enforcement membrane for AI-generated or AI-agent software. All other use — internal use, research, education, evaluation, and non-competing commercial products that merely *depend on* the Licensed Work — is granted free of charge. |
| **Change Date** | The earlier of (a) four years from the release date of each version, or (b) a specific date counsel sets per release. |
| **Change License** | Apache License, Version 2.0 |

### Notes for counsel
- Confirm the *Competing Use* definition is narrow enough to be permissive (OSS-developer-first
  audience) yet protects the commercial safety-membrane surface.
- Confirm interaction with **patent pending** status — BSL's Change License (Apache-2.0) carries a
  patent grant on/after the Change Date; ensure this is intended for each released version.
- Decide whether the Change Date is per-release rolling (typical BSL) or a single fixed date.
- Add the standard BSL 1.1 "Covenants", "Notice", and disclaimer sections from the canonical text.

**Until counsel approves and `LICENSE` is replaced, this project remains Proprietary.**
