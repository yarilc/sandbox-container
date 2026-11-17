# Proposal

## Why

The Codex adoption of `sandbox-ref-23` (`adopt-sandbox-ref-23` in `codex-container`) ran the old Codex wrapper tests against the shared launcher core. One case found a lost behavior:
- **The case:** a state directory exists but the caller cannot enter it (for example `~/.codex` with mode `000`).
- **What the core does:** it stops with a raw Bash message, `launcher/core.sh: line 614: cd: <path>: Permission denied`. The message has no wrapper prefix and no hint.
- **What the old Codex launcher did:** it printed an actionable `codex-container:` error.

The reason is that the core resolves each state path with `cd` before its accessibility check runs. The same happens when a missing state directory cannot be created. The reference spec "Private credential directories" already requires a path-specific error with a repair hint, so the core does not meet its own spec. The shared test passed only because it checks that the path appears somewhere in stderr.

## What Changes

- **Accessibility check first.** `launcher/core.sh` checks each state directory for accessibility before resolving it. On failure it stops with a prefixed, path-specific error that suggests a fix, and the session never reaches the engine's image or container operations. The check covers:
  - the shared configuration directory;
  - every shared directory;
  - the isolated home and its children;
  - read-only state.
- **Creation failure.** A state directory that cannot be created stops with a prefixed error naming the path.
- **Shared tests.** `tests/test_launcher.py`'s inaccessible-state case asserts the prefix and the hint for each kind of state directory, plus the creation failure.
- **Tag.** The fix is tagged `sandbox-ref-24` after the operator's setups. Codex adopts `sandbox-ref-24` in its pending `adopt-sandbox-ref-23` change instead of `sandbox-ref-23`. The other wrappers adopt it in their own adoptions.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `persistent-state`:
  - "Private credential directories" covers inaccessible and uncreatable directories with a prefixed, actionable error;
  - "Read-only state" covers an existing but inaccessible directory.

## Impact

- **Code:** `launcher/core.sh` (state directory phase only) and `tests/test_launcher.py`.
- **Wrappers:** no wrapper-owned file changes. Claude stays on `sandbox-ref-23` until its next adoption. Codex picks the fix up before its adoption merges.
- **Qualification:** the core is part of the qualification identity, so installations rerun `--container-setup` after adopting the tag.
