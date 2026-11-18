## Why

The runtime image pins OpenSpec 1.16.0 (2026-10-30). OpenSpec 2.0.0 is the newest
stable release that was at least 72 hours old when the versions were frozen
(2026-11-18). This repository is the first of six coordinated bumps, and every
agent wrapper moves to 2.0.0 in its own change.

## What Changes

- `Containerfile`: `OPENSPEC_VERSION` moves from `1.16.0` to `2.0.0`. The base
  image digest stays as it is, because a separate change will review the sandbox
  image. The recipe gains no agent CLI.
- `tests/test_image_pins.py`: the version-range mutation follows the new pin.
- `docs/validation.md`: a dated maintenance entry records the versions, the
  image ID and the results. The image summary in the reference-shell section now
  names `@fission-ai/openspec@2.0.0`.
- **BREAKING (inside the image):** OpenSpec 2.0 no longer generates `/opsx:*`
  command files. It installs skills in `.agents/skills/` instead. The reference
  image has no agent, so nothing in it uses those files. The planning CLI on the
  operator's workspace moves to 2.0 at the end of the six-repository effort,
  outside this change.

No shared launcher file changes. No `sandbox-ref-*` tag is created, and the
untagged ShellCheck fix keeps waiting for the next change to the core.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. The `runtime-image` requirement "Runtime image inputs are pinned" already
requires the exact recorded version, and this change only records a new one.
The change sets `skip_specs: true`.

## Impact

- **Files:** `Containerfile`, `tests/test_image_pins.py`, `docs/validation.md`.
- **Image identity:** the runtime image and its build-inputs hash change. The
  operator reruns `--container-setup` on the three hosts.
- **Persistent state:** the persistent `~/.config/openspec` directory, mounted
  read-write, is kept. OpenSpec 2.0 must start with state written by 1.16.0.
- **Wrappers:** not touched. Each one gets its own change: Claude, Codex,
  OpenCode and Pi bump their agent CLI together with OpenSpec, and Antigravity
  bumps only OpenSpec.
