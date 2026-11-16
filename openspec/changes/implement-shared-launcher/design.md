# Design

## Context

See proposal.md for the motivation. `docs/launcher-contract.md` is the behavioral source of truth: phase tables, core rules, decisions U1-U18, visible changes and test map. This design covers only how the reference builds it.

Starting point in `sandbox-container`:
- `sandbox-container.sh` (896 lines) is a family A launcher: immediate shutdown from the trap, `control()` slicing, `capture_response`. It already has the U9 lifecycle, the lifetime clock and most union checks.
- `tests/test_wrapper.py` (80 cases) embeds its fake engine.
- `tests/sandbox_profile.py` builds a private fixture root whose wrapper is a stub that exits 1.
- `tests/fixtures/agent` (provider fixture with two methods) and `tests/fixtures/shell-agent` (no methods) exist for the shared Python tests.

## Goals / Non-Goals

**Goals:**
- `launcher/core.sh` implements every row of the contract that is not "reference: none" for a single agent, driven only by `agent/launcher.sh`.
- The shared tests prove agent-specific paths (provider mode, credentials, hooks, approval bypass, executable temporary storage) with the fixture agent part, since the reference shell profile does not exercise them.
- The reference stays usable after every task group.

**Non-Goals:**
- Changing any wrapper repository. Each wrapper adopts `sandbox-ref-22` in its own change.
- Unifying `container-entrypoint.sh`, the Containerfiles or the runtime tests (`test_runtime.py`, `test_network_runtime.py`).

## Decisions

1. **Refactor in place first, then converge phase by phase.**
   - The first core is the reference launcher moved into `launcher/core.sh`. Its literals (prefix, home, image, label, config directory) are replaced by `agent/launcher.sh` values, with no behavior change, so the 80 existing cases stay green.
   - Each later task group applies one or two contract phases and moves the matching tests.
   - Alternative rejected: writing the core from scratch and switching at the end. It leaves the reference untested for most of the change.
2. **Core layout.**
   - Phase functions (`core_arguments`, `core_settings`, `core_workspace_state`, `core_engine`, `core_mounts_image`, `core_create_start`, `core_shutdown`) and a short main sequence at the end, in contract order.
   - Globals follow the contract's "core state" names, so hooks read documented names only.
   - The entry script calls `source "$dir/launcher/core.sh" "$dir/agent/launcher.sh" "$@"`; the core sources the agent file first and shifts it off the arguments.
3. **One hook caller.**
   - `call_hook <name> <inputs...>` empties the hook's output arrays, runs the function only when `declare -F` finds it, and turns a nonzero status into `hook <name> failed`.
   - It then hands the outputs to one validator per hook: reserved names, mount rules, tmpfs sizes, build-argument values.
   - The shared tests drive every refusal through the fixture agent part.
4. **Fixture agent parts as the test surface.**
   - `tests/fixtures/agent/launcher.sh` defines every hook and every data array; its hooks record their inputs and visible variables to a file the tests read.
   - `tests/fixtures/shell-agent/launcher.sh` defines none.
   - `tests/sandbox_profile.fixture_root` copies `launcher/` and writes the real thin entry script under the fixture wrapper name, replacing today's stub.
5. **Shared fake engine.**
   - `tests/fake_podman.py` starts from the reference's embedded fake and adds the union of `FAKE_*` controls the moved tests need, with Antigravity's and Pi's files as the source for family B cases.
   - It rejects unknown commands, as Pi's does. The runtime harness keeps the real engine.
6. **Test migration follows `docs/launcher-test-map.md`.**
   - The reference's 80 cases move to `tests/test_launcher.py` as they are, or rewritten where the map says "shared (rewrite)".
   - The first occurrence of each "shared" case from C, X, A, O and P is ported. "Shared (duplicate)" cases are merged into the matching case.
   - The reference's `tests/test_wrapper.py` keeps only shell-profile and history checks.
   - A new U1 case covers the provider default.
7. **Shared Python changes ship with the core.** These change in the same tag, each with its own unit tests: profile schema (`native.exec`, `native.exec_tmp`, no `runtime_build`, new suffixes), installation manifest, qualification identity, preflight and managed-launch trust lists, default-mode derivation, and setup building through the wrapper.
8. **Tag only after the full runtime battery.** The tag `sandbox-ref-22` is created only after the unit discovery, every runner mode, a real build-only refresh and the operator's setup on the three hosts pass.

## Risks / Trade-offs

- [Behaviors that only agent wrappers reach, such as provider credentials or Pi's mounts, are verified here only against the fake engine] → The fixture agent part exercises each path; each adoption change then runs its wrapper's real runtime suites before deleting its old launcher.
- [A long change with a large test move can leave the suite red for a while] → Decision 1 keeps every task group green; each task names the cases it moves and runs them.
- [Bash library pitfalls: `set -e` inside functions called from conditionals, `local` hiding exit statuses, traps across `source`] → Traps and `set` options are owned by the entry and the core main sequence only. The core uses explicit status checks in the style of `capture_response`. The entry is tested by the help-without-readlink and symlink-invocation cases.
- [The union fake engine grows complex] → It is one file with a dispatch per command, and an unknown command fails the test.
- [Installed qualification changes for every user] → Visible change recorded; the operator reruns setup on the three hosts before the tag.

## Migration Plan

1. Implement and validate on a branch; merge into `main`.
2. The operator pushes and runs `--container-setup` on the three hosts.
3. Tag `sandbox-ref-22`, archive with spec sync.
4. Adoption changes: Claude first; then Codex, Antigravity and Pi; then OpenCode.

Rollback before the tag: revert the merge. After the tag: a corrective tag.
