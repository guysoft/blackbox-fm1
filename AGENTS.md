# blackbox-fm1

Read README.md, PROGRESS.md, META.md, RULES.md and docs/BLACKBOX-DEVELOPMENT.md.
This is an independent Felucca fork, not an upstream-supported hardware target.

Keep FM-1 behavior unchanged outside explicitly selected Blackbox builds.
Do not edit BSP/engine submodules in place; add a board adapter in this repository.
Use `.opencode/skills/porting-ac791n-firmware/SKILL.md` for new firmware ports.

No device writes before the first read-only hardware session and backup gate.
The user authorizes automatic iteration after one supervised first install;
do not ask for every normal repeat flash once the session is armed. Stop on
failed health checks. Recovery, stock restore, partition changes and factory-data
replacement are separate operations, not automatic fallbacks.

Keep source-inspected, host-tested and hardware-tested evidence distinct.
Never report audio or display correctness from identity alone.
Keep binaries/dumps/private data in ignored artifacts/, not Git.
Never install/upgrade system packages automatically; project dependencies use uv.
