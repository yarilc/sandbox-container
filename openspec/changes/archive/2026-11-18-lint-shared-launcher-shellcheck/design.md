# Design

## Context

ShellCheck 0.11.0 (`docker.io/koalaman/shellcheck@sha256:b9389b73c8f26f710a7171cb7d8848a34a9c1e07a7865e727c9ec4ce99f9a83f`) at warning level, checking each file alone, reports in the reference (2026-11-18):

- **`launcher/core.sh`:**
  - SC2148 on line 1 (no shebang or shell directive);
  - SC2154 for the nine variables that `capture_response` assigns with `printf -v`:
    - `runtime_info`, `cgroup_controllers`, `network_backend`, `network_version`, `network_platform`;
    - `image_hash`, `runtime_image_id`, `image_environment`, `configured_budgets`;
  - SC2154 for `wrapper_dir`, which the entry script sets before sourcing the core;
  - SC2209 for `temporary_exec=exec` in `core_mounts_image` (`exec` reads as the builtin);
  - SC2054 for two arrays holding unquoted `--mount` and `--tmpfs` option lists with commas.
- **`tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh`, `agent/launcher.sh`:**
  - SC2148;
  - SC2034 for every `AGENT_*` value;
  - in the hook fixture, SC2034 for the hook outputs (`agent_env`, `agent_mount_specs`, `agent_build_args`, ...).
- `sandbox-container.sh`, `tests/run-runtime.sh`, `tests/image-smoke.sh` and `network/build-guard.sh` are clean.

Only Pi's CI runs ShellCheck, through `ludeeus/action-shellcheck` with `scandir: .` and `severity: warning`, so it also scans the copied core and fixtures. Pi's and OpenCode's `agent/launcher.sh` already use `# shellcheck shell=bash disable=SC2034,SC2154`; Claude's, Codex's and Antigravity's do not.

`launcher/core.sh` is part of the qualified code identity. Any byte change is a new tag, propagation to five wrappers and `--container-setup` on three hosts for each. The user chose (2026-11-18) to commit this change without a tag of its own and let the next core-changing tag carry it.

## Goals / Non-Goals

**Goals:**
- Every shared launcher file passes ShellCheck at warning level alone, with the reason for every suppression written next to it.
- The reference can check any checkout the same way, with a pinned ShellCheck.

**Non-Goals:**
- Changing launcher behavior, messages or arguments.
- A tag, propagation or setup run for this change alone.
- Adding a CI workflow to the reference or to the wrappers without one.

## Decisions

1. **Narrow suppressions in the core.**
   - A file-level `# shellcheck shell=bash` directive replaces nothing else.
   - SC2154 is disabled on the command that reads each `capture_response` target, with a comment naming `capture_response`; a comment above `capture_response` explains the `printf -v` assignment. A file-level SC2154 disable is rejected: it would hide real unassigned variables.
   - `wrapper_dir` gets a directive at its use, naming the entry script.
   - SC2209 and SC2054 are fixed by quoting (`temporary_exec='noexec'` and `'exec'`; the `--mount` and `--tmpfs` option lists as quoted words), not suppressed. The values passed to Podman are unchanged.

   Alternative rejected: initializing every `capture_response` target before the call. It would silence SC2154 but adds code whose only purpose is lint, in a file whose bytes define qualification.
2. **Agent parts use Pi's directive.** `# shellcheck shell=bash disable=SC2034,SC2154`, with a comment that the core sources the file, reads its data and hook outputs and defines the state the hooks read. The same line goes into the fixtures and the reference's `agent/launcher.sh`; the wrappers add it to their own part when they adopt the tag that carries this change.
3. **`tools/shellcheck.sh <checkout>`.**
   - It runs the digest-pinned image with `podman run --rm --network=none` and the checkout mounted read-only at its own path.
   - It checks every tracked `*.sh` file, found with `git -C <checkout> ls-files '*.sh'`, at `-S warning`, and exits with ShellCheck's status.
   - It lives in `tools/`, which is never copied to the wrappers.
4. **Deferred tag.** The change is committed and archived on `main` without a tag. The next reference change that changes `launcher/core.sh` and takes a tag lists this change in its validation record. The wrappers then adopt both together, with one setup round.

## Risks / Trade-offs

- **[Pi's CI keeps failing until the next tag]** → Accepted by the user; it is a lint failure in copied files, not a behavior defect.
- **[A quoting change alters an argument]** → The unchanged shared launcher tests compare the engine arguments, including the tmpfs options, and must pass.
- **[The pinned image ages]** → The digest is recorded in the tool and in this design. A ShellCheck update is a deliberate edit of the tool.

## Migration Plan

1. Edit the four files, add the tool, and run it on the reference and on the five wrapper checkouts (read-only, to record their findings).
2. Run the shared launcher tests and the alignment test unchanged.
3. Commit on `main` without a tag, and archive the change.
4. The next tagged reference change carries it. The wrappers then add the directive to their own `agent/launcher.sh`, if it is missing, in that adoption.
