# Proposal

## Why

OpenCode's adoption of `sandbox-ref-20` found a defect in the shared `tests/test_guard.py`. `production_container` runs the checkout's real agent image but mounts the writable native home of the fixture profile (`/fixture-home`) instead of the wrapper's home. An agent that writes to its home at startup fails on the read-only root file system: OpenCode's `test_production_filter_and_landlock_on_real_rootless_kernel` fails with `EROFS: read-only file system, mkdir '/opencode-home/.local'`. Claude, Codex, Antigravity and Pi pass only because their version commands do not write to their home.

## What Changes

- `tests/test_guard.py` (`production_container`) mounts the writable home of the checkout's real profile, which belongs to the real image it runs. `tests/sandbox_profile.py` exposes it as `AGENT_HOME`, next to `AGENT_COMMAND`, so shared tests keep reading no checkout profile directly.
- The change ends with the annotated tag `sandbox-ref-21`. Every wrapper then adopts `sandbox-ref-21` in its own change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `reference-propagation`: shared tests that run a checkout's real image use that checkout's real profile for the image's layout.

## Impact

- Shared files: `tests/test_guard.py` and `tests/sandbox_profile.py` (new tag needed; wrappers adopt it with `tools/propagate.py`).
- No production code, image, profile or qualification identity changes, so installations need no new setup.
