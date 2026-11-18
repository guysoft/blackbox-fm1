# Porting skill validation

Three read-only scenarios were answered by a baseline agent before creating the
skill and by an agent given the skill afterwards:

1. Rename/flash on the basis of a matching SoC, target absent.
2. Claim full unattended audio/display validation from one flash and identity.
3. Reuse an unlicensed UI and assume an unfamiliar target uses V20 offsets.

Both runs rejected those shortcuts. The with-skill run additionally cited this
repository's exact V20/V23 ranges and OTA staging overlap. The broad safety
rubric was already passed by the baseline; **no measured improvement is claimed**.
The scenarios are a smoke check, not evidence of physical port success or a
statistical skill benchmark. Agent token/timing measurements were not supplied.

The technical regression motivating the reference guidance was observed directly:
both reference unpackers assumed an app base of 0x4000 and failed on the pinned
V23 package. Our boot-directory-derived parser handles its 0x6000 base, with
synthetic tests for both bases and real-package checks.

Review feedback incorporated: half-open ranges; explicit staging destruction;
locate exact digest/profile definitions; installed-base check in the loader;
4 KiB / 8 KiB RAM/pool margins; distinguish session authorization from per-attempt
arming; require recovery evidence for this project's automatic sessions.

Prompts live in `.opencode/skills/porting-ac791n-firmware/evals/evals.json`.
Generated review artifacts are kept under artifacts/skill-evals/.
