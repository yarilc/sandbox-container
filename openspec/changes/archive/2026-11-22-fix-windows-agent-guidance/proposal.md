# Proposal

## Why

Planning the Claude adoption of `sandbox-ref-27` found three gaps that only
an agent wrapper shows on Windows.

- **Setup's authentication guidance names Linux commands.** Setup started by
  the Windows entry still prints:
  - for a declined login, the next action as the managed command in the
    machine, for example
    `/home/user/.local/bin/claude-container auth login --claudeai`;
  - for the API method, the generic "existing runtime environment mechanism".

  From Windows, the step is `claude-container.ps1 auth login --claudeai`, and
  the key is `$env:ANTHROPIC_API_KEY` before the entry.
- **`tools/windows-validate.ps1` passes `-c` to the agent.** It runs its
  command cases as `& $E -c '...'`. In an agent wrapper, every
  non-`--container-*` argument goes to the agent (`claude -c`). The script
  cannot validate an agent wrapper.
- **`tools/propagate.py` misses runner modes.** It recognizes only
  `== --mode ]]`. Claude's runner offers `--guard` as
  `"${1:-}" == --guard || "${1:-}" == --guard-idle`, so the dry run omitted
  `--guard` although `network/guard.c` changed.

The first gap is in shared code. It is fixed here, under `sandbox-ref-28`,
before the wrappers adopt the Windows support.

## What Changes

- **Authentication guidance from the Windows entry** (`setup/setup.py`).
  With `WRAPPER_WINDOWS_SETUP=1`:
  - a pending login names `<name>.ps1` with the login arguments, or
    `<name>.ps1` alone for an interactive sign-in;
  - the API method names `$env:<KEY> = '...'` before `<name>.ps1` in
    PowerShell.

  Setup from a Linux shell keeps its messages.
- **Agent wrappers in `tools/windows-validate.ps1`.** When the profile's
  `native.command` is not `bash`, the cases that run a command add
  `--container-shell` before `-c`.
- **Runner modes in `tools/propagate.py`.** A mode written as `== --mode`
  followed by `||` or `]]` is recognized.
- Tag `sandbox-ref-28` after the checks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `container-setup`: "Setup started by the Windows entry" also gives the
  authentication next steps for Windows.
- `reference-propagation`: "Verification checklist after adoption" recognizes
  the modes of a runner that tests two modes in one condition.

## Impact

- `setup/setup.py` and `tests/test_setup.py` (shared): a new tag,
  `sandbox-ref-28`.
- `tools/windows-validate.ps1`, `tools/propagate.py` and
  `tests/test_propagate.py` (reference-only).
- `docs/setup.md`, `docs/propagation.md` if needed, and `docs/validation.md`.
- The wrappers adopt `sandbox-ref-28` instead of `sandbox-ref-27`. Claude's
  adoption is planned in `claude-container`, as `adopt-sandbox-ref-28`.
