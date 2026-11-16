# Design

## Context

See proposal.md for the motivation. Observed state (2026-11-16, after `sandbox-ref-21`):

- All six launchers accept the same eight `--container-*` options (`build`, `git-worktree`, `help`, `qualify`, `qualify-probe`, `setup`, `shell`, `toolchain`). They share about twenty `<PREFIX>_*` variables: budgets, network, state, toolchains, CA, Podman access, lifetime and maintenance.
- Agent-specific variables:
  - OpenCode: `AGENTS_DIR`, `ENV_VARS`, `PROVIDER`, `SYSTEM_CONFIG`, `VERSION`, `YOLO`;
  - Pi: `GITCONFIG`, `YOLO`;
  - the reference has no provider-mode variables.
- Only six functions exist in all six launchers. The lifecycle helpers fall into two families:
  - **A** (sandbox, Claude, partly OpenCode): `shutdown`, `control`, `capture_response`, `creation_lookup`, `recover_container`;
  - **B** (Codex, Antigravity, Pi): `cleanup`, `record_signal`, `recover_container_by_label`, `recover_container_id`, `wait_for_client_until`, and in Codex and Pi also `wait_for_create`.
- Agent-specific helpers include OpenCode's `add_bind`, `opt_in_integration`, `shared_state` and `build_current_image`, and Pi's `select_ca_bundle`, `build_runtime_image` and `select_setting`.
- `setup/launch.py` (shared) execs `bash <wrapper> …` for managed installations, so the entry script name and its arguments must stay as they are.
- Wrapper tests:
  - Antigravity and Pi use `tests/fake_podman.py`; the others embed the fake engine in `tests/test_wrapper.py`.
  - Each `test_wrapper.py` has 1,521–1,873 lines.

The user decided the goal (near-total unification: wrappers reduced to data and a few hooks) and the language (Bash core, no new host requirement).

## Goals / Non-Goals

**Goals:**
- A complete, reviewed list of launcher differences, each with a decision.
- The `shared-launcher` contract: file layout, profile bridge, hook surface, common interface and shared tests, precise enough to implement the core without new design decisions.
- The list of spec deltas the implementation change must write for every behavior the reconciliation changes. The specs themselves change in that change, together with the code.

**Non-Goals:**
- Writing the core, the shared tests or the fake engine; tagging.
- `container-entrypoint.sh`, `Containerfile` and the runtime tests (`test_runtime.py`, `test_network_runtime.py`). They may be unified later, with the same method.
- Changing any wrapper repository.

## Decisions

1. **Inventory by phase, with the tests as evidence.**
   - Each launcher is read in the same seven phases:
     1. arguments and help;
     2. modes, budgets and lifetime;
     3. workspace and isolated-state checks;
     4. engine and cgroup checks;
     5. mounts, toolchains, CA and image;
     6. creation, budget verification and start;
     7. signals, shutdown and recovery.
   - Each behavior is checked against the wrapper tests that cover it. A behavior tested in one family and absent from the other is a candidate gap, not automatically a defect.
   - Alternative rejected: a line diff alone. It shows the drift but not which behavior is correct.
2. **Decision rule for each difference.**
   - Same behavior, different code: the core takes the more robust implementation, citing the test that shows it.
   - Behavior present in one family only: the core takes the union, unless the two conflict.
   - Behavior needed by one agent only: it moves behind a named hook.
   - Conflicting or user-visible choices are asked of the user during apply and recorded with the answer.
3. **Layout.**
   - The core is a new shared directory, `launcher/`, added to the shared directories and to the reference-copy manifest.
   - The agent part is `agent/launcher.sh`, next to `agent/profile.json`.
   - The entry script stays `<wrapper>-container.sh`, so `setup/launch.py`, the managed launchers and the documented commands do not change.
   - Alternative rejected: keeping the core under `setup/`. It would mix Python modules run by setup with the Bash code every session sources.
4. **Profile bridge as static Bash data plus an alignment test.**
   - `agent/launcher.sh` declares the values the core needs. A shared test compares them with `agent/profile.json`.
   - Alternative rejected: generating the file at setup time. Unrestricted installations may run without host Python, and a generated file would hide drift until setup.
5. **The core owns the process.** It owns `set` options, traps, the child table and the exit status. Hooks are plain functions called at fixed points; they receive inputs as arguments and return results in named arrays or variables, as the contract defines. This keeps one lifecycle and makes "No hook replaces the session lifecycle" checkable.
6. **One shared fake engine.** The shared launcher tests use one fake engine file. The inventory compares the embedded fakes with `tests/fake_podman.py` and records which cases each supports. The shared one must support the union of the cases the shared tests need.

7. **Independent review before archive.** An independent read-only review checks the document against the launchers, tests and specs. Every finding is resolved in the document or recorded as a deliberate loss in "Visible changes". Alternative rejected: deferring findings to the implementation change, where they would surface as late as the adoption defects of `sandbox-ref-19` to `-21`.

## Risks / Trade-offs

- [The inventory grows too large to review] → Work phase by phase, and record decisions in the document as each phase closes; the user reviews per phase.
- [A reconciled behavior changes what users of one wrapper see, for example a different message or status] → Record it in the document's "visible changes" list and its spec delta in the list for the implementation change, so each adoption change names it.
- [Bash as a library language: global state, `set -e` interactions] → Decision 5 keeps all process state in the core. The contract lists every variable a hook may read or set.
- [The inventory misses agent behavior (the review found unrecorded Pi, OpenCode and Antigravity paths)] → The "Review findings" section; each adoption change re-checks its launcher against the contract before deleting code.
- [Hooks become a back door for divergence] → The contract fixes the hook list. A new hook needs a reference change, and the shared tests run the core with a fixture agent part that defines none of the optional hooks and one that defines all of them.

## Migration Plan

This change ships documents only and is archived without spec sync. Then:

1. `sandbox-container` implements the core, the shared fake engine and the shared launcher tests under a new tag.
2. Claude adopts first, being the closest to the reference.
3. Codex, Antigravity and Pi adopt next.
4. OpenCode adopts last.

Each adoption moves the wrapper's behavior into `agent/launcher.sh` and deletes the duplicated tests.
