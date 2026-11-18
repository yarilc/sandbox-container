# Proposal

## Why

ShellCheck at warning level, checking each file alone, reports findings in the shared launcher files that every wrapper copies:
- **`launcher/core.sh`:** no shell directive (SC2148, an error); variables assigned through `capture_response`'s `printf -v` and the entry script's `wrapper_dir` seen as unassigned (SC2154); an unquoted `exec` value (SC2209); unquoted `--mount` and `--tmpfs` option lists in arrays (SC2054).
- **`tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh` and the reference's `agent/launcher.sh`:** no shell directive (SC2148) and profile data or hook outputs seen as unused (SC2034).

Pi's CI scans the whole tree with ShellCheck, so these copied files fail it. Pi's and OpenCode's own `agent/launcher.sh` already carry a directive. The reference has no ShellCheck check of its own, so new findings in the core go unnoticed.

## What Changes

- `launcher/core.sh`:
  - gains a `shell=bash` directive;
  - gets narrow, commented directives where `capture_response` assigns through `printf -v` and where the entry script defines `wrapper_dir`;
  - quotes the `noexec` and `exec` values and the `--mount` and `--tmpfs` option lists.

  No command, argument or message changes.
- The two launcher fixtures and the reference's `agent/launcher.sh` gain the directive Pi uses: `shell=bash`, with `SC2034` (data the core reads) and `SC2154` (core state the hooks read) disabled.
- New reference-only tool `tools/shellcheck.sh`. It runs ShellCheck 0.11.0 from a digest-pinned image through Podman at warning level on every `*.sh` file of a checkout given as its argument, so the reference and any wrapper can be checked the same way.
- No tag of its own. The changed files ride with the next reference change that changes the core and takes a new tag, so the wrappers propagate and rerun setup once. When they adopt it, Claude, Codex and Antigravity add the same directive to their own `agent/launcher.sh`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `shared-launcher`: the shared launcher files and every agent launcher part pass ShellCheck at warning level when checked alone, and the reference provides the check.

## Impact

- **Code:**
  - `launcher/core.sh`;
  - `tests/fixtures/agent/launcher.sh`;
  - `tests/fixtures/shell-agent/launcher.sh`;
  - `agent/launcher.sh`;
  - new `tools/shellcheck.sh`.

  The wrappers' reference-copy manifests move with the next tag, as for any shared change.
- **Behavior:** none. The shared launcher tests stay unchanged and must pass unchanged.
- **Qualification:** the core's bytes change, so the reference's qualification identity changes. Wrappers are affected only when they adopt the next tag.
- **Docs:** `AGENTS.md` (lint command) and `docs/launcher-contract.md` (the directive in the agent part).
