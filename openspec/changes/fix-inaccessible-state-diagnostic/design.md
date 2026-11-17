# Design

## Context

`core_state_directories` in `launcher/core.sh` handles each kind of state directory in the same order:

1. It creates the directory (`create_private_directory`, a `mkdir -p` subshell).
2. It resolves the directory with `$(cd -- "$path" && pwd -P)`.
3. Only then does it run `private_directory`, which checks access, owner and mode.

The read-only path (`core_readonly_state`) resolves with `cd` after a plain `-d` test. Under `set -Eeuo pipefail` a failing `cd` or `mkdir` ends the launcher with Bash's own message:
- `cd` fails on a directory that exists but cannot be searched;
- `mkdir` fails when the parent is not writable.

The four resolution points are the isolated home, the configuration directory, the shared directories and the read-only sources. Isolated-home children are checked with `readlink -m` and `private_directory` without `cd`, but their creation can still fail raw.

The old Codex launcher checked access before resolving, so its `test_inaccessible_state` asserted the wrapper prefix. The shared `test_inaccessible_state_and_ignored_permissions` asserts only that the path appears in stderr, which Bash's message also satisfies.

## Goals / Non-Goals

**Goals:**
- Every state directory failure stops with a `<wrapper>:` diagnostic that names the path and gives a hint. The engine never sees an image or container operation.
- The shared tests fail on a raw shell error.

**Non-Goals:**
- Changing ownership or privacy rules, or adding checks to read-only state beyond accessibility.
- Changing the workspace or toolchain library checks. Those are not state directories and already report their own errors.

## Decisions

1. **One helper resolves state paths.** `resolve_state_directory <path>` is called at the four resolution points. It:
   - tests `-d`, `-r` and `-x` before any `cd`;
   - stops with `state directory is not accessible: <path> (grant your user read and search access, or choose another directory)`;
   - otherwise prints `pwd -P`.

   `private_directory` keeps its own checks for write access, owner and mode. Its existing "not accessible" message gets the same hint, so both paths read alike. Alternative rejected: `cd ... || die`. That still prints Bash's `cd:` line before the wrapper message.

2. **Creation failure.** `create_private_directory` runs `mkdir -p -- "$path" 2>/dev/null || die "cannot create state directory: <path> (check the parent's permissions or choose another directory)"`. The `die` runs in the caller, not in the subshell, so the umask stays scoped to the subshell (requirement "Private state creation preserves the host process umask").

3. **Read-only state.** `core_readonly_state` keeps "needs an existing directory" for a missing directory and uses the helper for an existing one.

4. **Shared test.** `test_inaccessible_state_and_ignored_permissions` becomes a subtest matrix for the shell reference, the fixture agent profile, or both. Each case asserts all of the following:
   - nonzero status;
   - the `sandbox-container:` (or fixture) prefix;
   - the path;
   - the hint;
   - no `Permission denied` from the shell;
   - no image, build or create call.

   The cases are:
   - the shared configuration directory at mode `000`;
   - a shared directory (`.config/openspec`) at mode `000`;
   - the isolated home at mode `000`;
   - an isolated child (`.config/sandbox-container`) at mode `000`;
   - read-only state with an inaccessible configuration directory;
   - an absent configuration directory below a parent at mode `500`.

   The ignored-permissions half stays as it is. Root bypasses these checks, so the test keeps the existing root skip.

5. **Release.** The change is merged on `main`, the operator runs setup on the three hosts, and the merge is tagged `sandbox-ref-24`. Codex's pending adoption then propagates `sandbox-ref-23` to `sandbox-ref-24` and reruns its old-test classification.

## Risks / Trade-offs

- **[A directory readable but not searchable, or the reverse]** → The helper requires both `-r` and `-x`, as `private_directory` already does. A directory that only allowed `cd` was never usable as a mount source anyway.
- **[`mkdir -p` error text hidden]** → The wrapper message names the directory that was asked for, not the deepest parent that failed. The operator sees the requested path and the hint to check its parents.
