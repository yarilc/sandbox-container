# Design

## Context

See proposal.md for the motivation. The facts below shape the approach.

**The working session of this change.**
- It is a `claude-container` session that Windows started in the Podman
  machine, with WSL2 as backend, on the workspace `D:\Workspace\sandboxes`
  (9p/drvfs, executable).
- `$HOME`, `/tmp` and `/var/tmp` are `noexec` tmpfs.
- The toolchain library is empty, so the session has no container engine,
  and `podman` answers `operation not permitted`.
- Python is 3.11.

On 2026-11-26, `tests.test_propagate` and `tests.test_adoption_run` ran in
this session:
- with `SANDBOX_TEST_TMPDIR` under `$HOME`, 6 runner tests failed: the
  `podman` stub on `noexec` storage cannot run, so bash finds the real
  client;
- with `SANDBOX_TEST_TMPDIR` on the workspace mount, all 35 passed, in
  122 s.

**Where the contracts name other environments:**
- `reference-propagation`: the pre-tag runs on WSL and on a native Linux
  host, and the one-native-host adoption perimeter;
- `docs/propagation.md`, steps 1 and 3;
- the reference's `AGENTS.md` lines 80-81 (adoption on one host), 114
  (Windows host) and 209-212 (interactive session "opened on that host");
- the same Windows line in every wrapper, and the session line in
  `claude-container` and `codex-container`;
- Antigravity's "operator-run" authenticated checks and its "interactive host
  launch".

**What already fits.**
- `shared-launcher` asks for Windows PowerShell 5.1 "on a Windows host",
  recorded per tag, without timing it before the tag.
- The `## OpenSpec Workflow` sections of Codex, OpenCode and Pi cover
  artifact coherence, apply and archive, and name no environment. They stay
  as they are.

**Who reads which file.**
- No repository has a `CLAUDE.md`. Claude Code loads `CLAUDE.md`, and follows
  `@path` imports in it.
- Codex, OpenCode and Pi read `AGENTS.md`.

**Tests that touch these files.**
- No test reads `AGENTS.md` text.
- The shared `tests/guard_terminal_probe.py:60` sends the reader to
  "AGENTS.md, Testing Guidelines".
- `tests/test_alignment.py` checks every tracked text file for carriage
  returns.

**Precedent for cross-repository tasks.** `align-parity-table` (2026-11-11)
was a reference change whose tasks opened one branch per sibling and verified
each one.

## Goals / Non-Goals

**Goals:**
- One section of guidelines, with the same body in the six repositories, that
  every agent loads.
- No guideline line left that asks for another environment inside a change.
- Propagation output that already separates the session checks from the
  follow-up, so adoptions copy the right shape.

**Non-Goals:**
- No change to shared files (`network/`, `setup/`, `launcher/`, shared
  tests), so no new tag. This includes the pointer in
  `tests/guard_terminal_probe.py`.
- No change to `tools/adoption-run.sh`, to the `--checklist` lines, or to the
  wrappers' specs.
- No `openspec/config.yaml` rules: the user chose `AGENTS.md` as the carrier.
- No toolchain library for the session. Images that would give the session
  an engine are an operator choice, outside this change.
- No rewrite of history: `docs/validation.md`, archived changes and
  `todo.md` keep their text.

## Decisions

1. **One reference change, with a task group for the wrappers.**
   - **Where the contract lives:** in the reference specs
     (`change-validation`, `reference-propagation`).
   - **How the wrappers are changed:** the tasks open a branch
     `close-changes-in-working-session` in each wrapper, with one commit for
     `AGENTS.md` and `CLAUDE.md`. They verify it there, as
     `align-parity-table` did. The user pushes and merges.
   - **The edit-root default:** the scaffold's `allowedEditRoots` default
     (this repository only) is overridden by that precedent.
   - **Rejected: five loose commits.** Nothing would track that all five
     were done.
   - **Rejected: six OpenSpec changes.** That is five extra sets of planning
     artifacts for one section, and no wrapper spec needs a delta.

2. **One section, the same body everywhere.** The section is named "Change
   workflow and validation environments":
   - **Heading level:** a `##` section in the five repositories that use
     `##` headings, and a `#` section in Antigravity, whose `AGENTS.md` uses
     `#` headings and bullets.
   - **Same body:** the body is identical in all six, so the tasks can
     compare it by SHA-256.
   - **Placement:** immediately before `## Testing Guidelines`, so the
     testing guidance reads inside the rule. All five `##` repositories have
     that section. In Antigravity, it goes right after
     `# Language conventions`.
   - **Reference-only text:** the sentence about tags goes outside the
     section, in the reference's propagation paragraph and in
     `docs/propagation.md`.

   The body:

   ```markdown
   A change is validated and closed in the environment where it is
   developed: the session the work runs in. Once a change is applied, no
   task waits for another environment or for the operator: not the WSL host
   outside the session, a native Linux host, a Windows host, nor a real
   installation.

   - **Before the change starts:** while exploring, proposing or designing,
     a spike may run on another environment to answer one specific
     question. The design records the question, the environment, the
     command and the result. A spike is never a task.
   - **During the change:** run every check the session supports. A check
     the session cannot run, or one that fails because of the session's
     environment, is recorded in `docs/validation.md` as unavailable in the
     session, with its reason. It moves to the follow-up and does not block
     closure. A failure caused by the change is fixed in the change.
   - **Test storage in a session:** `$HOME`, `/tmp` and `/var/tmp` are
     `noexec` there. Point `SANDBOX_TEST_TMPDIR` at a new directory on the
     workspace mount, and remove it afterwards, or tests with stubs fail for
     the session's reasons.
   - **After closure:** runs on other environments are follow-up
     verification:
     - runner modes on WSL and on the native Linux host;
     - `tools/adoption-run.sh`;
     - `tools/windows-validate.ps1` on Windows PowerShell 5.1;
     - sessions opened on another host;
     - operator checks with real accounts.

     `tasks.md` lists them as plain bullets under "Follow-up after
     closure", never as checkboxes. `docs/validation.md` lists them as
     pending, then their results. A defect they find opens a new change.

   `CLAUDE.md` imports this file for Claude Code and holds nothing else:
   edit only `AGENTS.md`.
   ```

   - **Rejected: a short pointer to a reference document.** An agent working
     in a wrapper would need a second file from another repository to know
     the rule.

3. **`CLAUDE.md` is the one line `@AGENTS.md`.**
   - It is LF-terminated, so the carriage-return check passes.
   - **Rejected: a full copy with a check.** The check would belong in the
     shared `tests/test_alignment.py`, so it would need a tag and five
     adoptions. A check in `tools/` runs only when someone runs it.
   - **Rejected: a symbolic link.** The checkouts are on NTFS, and Windows
     checkouts create links only with `core.symlinks` and the right
     privileges.

4. **Conflicting lines are reworded in place, not deleted.** Each keeps its
   technical content and names the timing.
   - **Windows PowerShell 5.1:** "...; Windows PowerShell 5.1 itself is
     validated on a Windows host, as follow-up after closure." This applies
     to all six repositories; Antigravity has it inside its PowerShell
     bullet.
   - **Interactive session (reference, Claude, Codex):** the sentence stays
     in "Testing Guidelines", so the shared probe's pointer stays valid. The
     session opened on that host with its own client becomes the follow-up
     evidence for the `container-isolation` scenario, collected after
     closure.
   - **The runner (reference `AGENTS.md` and `README.md`):**
     `tools/adoption-run.sh` runs an adoption's checklist on WSL or the
     native Linux host, as follow-up after the adoption closes.
   - **Antigravity:** its authenticated Google account and Gemini API-key
     checks, and its interactive host launch, are operator follow-up after
     closure.

5. **Tag gate (A) in `docs/propagation.md`.**
   - **Step 1, before the tag:** run in the working session every checklist
     mode for the changed shared files that the session can run, in full.
     Record the others as unavailable, with the reason. Tag when the change
     closes.
   - **Step 1, after the tag:** the same modes run in full on WSL and on the
     native Linux host, as follow-up, recorded under the tag's section.
     Adoptions do not wait for them.
   - **Step 3:** an adoption is validated in the working session. The runner
     line and the manual steps are follow-up. A shared defect found by the
     session stops the adoption as today. A shared defect found by the
     follow-up, after the adoption merged, needs a new reference change, a
     new tag and a new adoption.
   - **`[not in target]`:** the paragraph on reference changes names
     `change-validation` beside `reference-propagation` as reference-only
     capabilities. Wrappers carry the rule in `AGENTS.md`, and their
     adoptions skip these deltas.

6. **Report shape in `tools/propagate.py`.** Only `report()` changes:
   - **Session commands:** `Prepare in the target:` and `Run in the target:`
     become `Prepare in the session:` and `Run in the session:`.
     `Images needed:` stays.
   - **Follow-up:** `Manual: ...` and `On one host, after the adoption: ...`
     are replaced by one block, `Follow-up after closure:`, of plain
     bullets:
     - `- on WSL or the native Linux host, from sandbox-container: bash tools/adoption-run.sh <target> <old> <new>`;
     - one bullet per manual step, with the existing `WINDOWS_STEP` text.

     The same bullets can be pasted under "Follow-up after closure" in
     `tasks.md`.
   - **Record template:** the table keeps one row per session command
     (`unit` and `mode` entries). The manual rows move out of it. After the
     table comes `Follow-up after closure:`, with the same bullets, each
     ending in `: pending`.
   - **`--checklist`:** the entries, their kinds (`manual` included) and
     the tab-separated lines are unchanged, so `tools/adoption-run.sh` and
     `tests/test_adoption_run.py` need nothing.
   - **Rejected: a new entry kind `followup`.** It would change the runner
     and its tests for no new information: the runner already skips manual
     entries with a note.

7. **`adoption-runner` gets no delta.** Its requirements describe the
   runner's behavior, which does not change. Only its `## Purpose` names the
   runner as the adoption's validation. The tasks edit that paragraph in the
   main spec directly, as OpenSpec does for a capability's purpose: the
   runner runs an adoption's follow-up verification on WSL or a native Linux
   host after the adoption closes in the working session.

8. **This change follows its own rule.**
   - **Session checks:**
     - `tests.test_propagate` and `tests.test_adoption_run`, with
       `SANDBOX_TEST_TMPDIR` on the workspace mount;
     - the reference's unit discovery in the same way;
     - `openspec validate --strict`;
     - `git diff --check` in each repository;
     - the SHA-256 comparison of the section body.
   - **Lint:** no `*.sh` or `*.ps1` file changes, so ShellCheck and
     PSScriptAnalyzer, which need an engine, are not required. The record
     says so.
   - **Follow-up:** none, because no runtime code changes.

## Risks / Trade-offs

- **A tag reaches the wrappers before the native hosts run it.** Mitigation:
  the follow-up runs the tag's modes first in the reference, and a shared
  defect gets a new tag through the existing "fix here first" path. The cost
  is one more adoption, instead of hours of waiting in every change.
- **A session without an engine verifies little runtime behavior.**
  Mitigation: the record says what was unavailable, and the follow-up lists
  it, so nothing is silently skipped. A session started with the test images
  in its library can run most modes. In the 2026-11-24 record, the unit
  discovery (559 tests) and every mode ran from such a session, with their
  environmental failures recorded. The exceptions were `--setup-runtime` and
  the engine cases, which need nested engines. Starting such a session is an
  operator choice.
- **"Fails because of the session's environment" can hide a real defect.**
  Mitigation: the record must name the cause, as the `cgroupfs` budget
  subtests are recorded today. A failure that the change's code can explain
  blocks closure (spec `change-validation`, "Failure from the change").
- **The body of the section drifts between repositories.** Mitigation: the
  tasks compare it by SHA-256 now. A later edit follows the same rule as the
  parity table: it is made in all six. No automated check is added, because
  it would have to be shared (see decision 3).
- **Claude Code's import syntax.** If the import stopped working, Claude
  would lose the guidelines silently. Mitigation: the tasks check it in this
  session, which runs Claude Code, by opening a file of one wrapper and
  confirming that the guidelines load.

## Migration Plan

- **Existing changes:** none to migrate.
  - The reference's `add-read-only-dependency-mirror` has only a proposal,
    and will follow the rule when its tasks are written.
  - Antigravity's `adopt-sandbox-ref-36` already lists its host and Windows
    runs as plain follow-up bullets.
- **OpenCode and Pi:** their pending adoptions of `sandbox-ref-36` use the
  new report and perimeter.
- **Rollback:** revert the reference commit and each wrapper's commit. Nothing
  else depends on the new files.
