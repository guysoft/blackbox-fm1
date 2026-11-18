# Development rules

- Preserve Felucca attribution, GPL and submodule licences.
- Pin upstream references and binary downloads with checksums.
- Board-specific register access stays in firmware/boards/blackbox/.
- Test portable input/protocol code on the host and compile the target.
- New Python behavior needs pytest coverage; manage dependencies with uv.
- Keep update loader, package limits and storage boundaries consistent.
- A matching chip or product name is not evidence of board compatibility.
- Normal automatic flashes require a hardware-qualified session and exact port.
- Fail closed; do not automatically retry a failed flash or run recovery writes.
- Back up factory calibration/device identifiers and user data separately.
- Do not copy Harbor code without a clear reuse licence/permission.
