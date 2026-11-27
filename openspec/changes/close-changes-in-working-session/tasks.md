# Tasks

Every task runs in the working session. Tests that use stubs set
`SANDBOX_TEST_TMPDIR` to a new directory on the workspace mount, for example
`/mnt/d/Workspace/sandboxes/.scratch/<name>`, which is removed afterwards
(design, Context). Work happens on the branch `close-changes-in-working-session`
in each repository.

## 1. Guidelines in the reference

- [x] 1.1 Create the branch `close-changes-in-working-session` in
  `sandbox-container`. Add the section `## Change workflow and validation
  environments` to `AGENTS.md`, immediately before `## Testing Guidelines`,
  with the body of design decision 2. Add `CLAUDE.md` holding only
  `@AGENTS.md` and a line feed.
  - **Verify:**
    - the heading occurs once;
    - `printf '@AGENTS.md\n' | cmp - CLAUDE.md` passes;
    - `python3 -B -m unittest tests.test_alignment` passes, with its
      carriage-return check.
- [x] 1.2 Reword the reference's conflicting lines as follow-up (design
  decision 4):
  - `AGENTS.md` lines 80-81, the runner;
  - `AGENTS.md` line 114, Windows PowerShell 5.1;
  - `AGENTS.md` lines 209-212, the interactive session, kept in
    `## Testing Guidelines`;
  - the runner sentence in `README.md` (lines 1235-1236).
  - **Verify:**
    - `grep -nE 'on one host|validated on a Windows host\.|opened on that host' AGENTS.md README.md`
      lists only lines that name the follow-up after closure;
    - the sentence that `tests/guard_terminal_probe.py` points to is still
      under `## Testing Guidelines`.
- [x] 1.3 Check in the working session that Claude Code loads the guidelines
  through the import (design, Risks). Read a file of `sandbox-container` in
  this session, or in a new Claude session in the same container, and look
  for the `AGENTS.md` text loaded from `CLAUDE.md`.
  - **Verify:** the observation, loaded or not and in which session, is
    noted for the record of task 5.2. When it does not load, the record names
    that, and the task still completes. The import is the user's decision,
    and the file is harmless.

## 2. Procedure and contracts in the reference

- [x] 2.1 Rewrite steps 1 and 3 of `docs/propagation.md` for the tag gate and
  the adoption perimeter (design decision 5).
  - **Step 1:**
    - the session runs come before the tag;
    - unavailable modes are recorded with their reason;
    - the tag is created at closure;
    - the full modes run on WSL and on the native Linux host after the
      tag, recorded under the tag's section;
    - adoptions do not wait.
  - **Step 3:**
    - the adoption is validated in the working session;
    - the runner line and the manual steps are follow-up after closure;
    - a shared defect found by the follow-up gets a new reference change,
      a new tag and a new adoption.
  - **`[not in target]`:** the paragraph names `change-validation` and
    `reference-propagation` as reference-only capabilities that adoptions
    skip.
  - **Verify:**
    - step 1 names the checklist as the minimum set, the qualification
      rule, the working session and the two native hosts after the tag
      (scenario "Procedure states the rule");
    - step 3 names the working session, the record of the commands not run
      and the runner as follow-up (scenario "Maintainer reads the
      verification step").
- [x] 2.2 Replace the `## Purpose` paragraph of
  `openspec/specs/adoption-runner/spec.md` with the follow-up role of
  design decision 7. Leave its requirements unchanged.
  - **Verify:**
    - `openspec show adoption-runner --type spec --json --no-scenarios`
      shows the new purpose and the same requirement names;
    - `openspec validate adoption-runner --type spec --strict` passes.

## 3. Propagation report

- [x] 3.1 Change `report()` in `tools/propagate.py` as design decision 6
  describes:
  - `Prepare in the session:` and `Run in the session:`;
  - one `Follow-up after closure:` block of plain bullets with the runner
    line and each manual step;
  - a record template whose table holds only the session commands,
    followed by the same bullets ending in `: pending`.

  Leave `checklist()`, `--checklist` and `WINDOWS_STEP` unchanged.
  - **Tests:** update `test_report_prints_commands_with_private_storage` in
    `tests/test_propagate.py`. Add tests for:
    - "Windows step is follow-up": no table row for the step, and a
      pending bullet;
    - "Follow-up block for the tasks": plain bullets and no `- [ ]`;
    - "Checklist lines for the runner": a manual step keeps the kind
      `manual` in `--checklist`.
  - **Verify:**
    - `python3 -B -m unittest tests.test_propagate tests.test_adoption_run`
      passes, with `SANDBOX_TEST_TMPDIR` on the workspace mount;
    - each new test fails when the follow-up block is removed from
      `report()`.
- [x] 3.2 Update the list of what the dry run prints in `docs/propagation.md`
  (step 2) and the "Fill in the validation-record template" paragraph (step
  3) to the new report.
  - **Verify:** every label the list names, `Run in the session:` and
    `Follow-up after closure:` included, appears in the output of
    `python3 -I tools/propagate.py ../pi-container sandbox-ref-28 sandbox-ref-36`.
    This is a dry run, and `pi-container` is unchanged afterwards:
    `git -C ../pi-container status --porcelain` is empty.

## 4. Guidelines in the wrappers

- [x] 4.1 In `claude-container`, `codex-container`, `opencode-container` and
  `pi-container`, create the branch `close-changes-in-working-session` from
  a clean `main`, then edit each one as design decisions 2 to 4 describe:
  - add the section immediately before `## Testing Guidelines`, with the
    same body as the reference;
  - add `CLAUDE.md`;
  - reword the Windows PowerShell 5.1 line;
  - in Claude and Codex, also reword the interactive-session sentence.
  - **Verify in each:**
    - the section body's SHA-256 equals the reference's;
    - `printf '@AGENTS.md\n' | cmp - CLAUDE.md` passes;
    - `git diff --check` is clean;
    - `python3 -B -m unittest tests.test_alignment` passes, with
      `SANDBOX_TEST_TMPDIR` on the workspace mount.
- [x] 4.2 In `antigravity-container`, on the same branch from a clean `main`:
  - add `# Change workflow and validation environments` right after
    `# Language conventions`, with the same body;
  - add `CLAUDE.md`;
  - reword the Windows PowerShell 5.1 clause of its PowerShell bullet;
  - reword the operator-run authenticated checks and the interactive host
    launch as follow-up after closure.
  - **Verify:**
    - the body's SHA-256 equals the reference's;
    - the `CLAUDE.md` comparison and `git diff --check` pass;
    - `python3 -B -m unittest tests.test_alignment` passes;
    - `grep -nE 'operator-run|interactive host launch|validated on a Windows host' AGENTS.md`
      lists only follow-up wording.
- [x] 4.3 Commit each wrapper's branch with the subject `State that changes
  close in the working session` and the co-author trailer.
  - **Verify:** `git -C <wrapper> status --porcelain` is empty, and the
    branch is one commit ahead of `main`, touching only `AGENTS.md` and
    `CLAUDE.md`.

## 5. Integration and record

- [x] 5.1 Check the six repositories together:
  - the extracted section bodies have one SHA-256 value;
  - the six `CLAUDE.md` files are identical;
  - `grep -nE 'on one host|validated on a Windows host\.|opened on that host|operator-run' */AGENTS.md`,
    from the workspace root, lists only follow-up wording.
  - **Verify:** the three outputs are kept for the record.
- [x] 5.2 Run the reference's unit discovery in the session, with
  `SANDBOX_TEST_TMPDIR` on the workspace mount. Also run
  `openspec validate close-changes-in-working-session --strict` and
  `git diff --check`.
  - **Record:** add a section for this change to `docs/validation.md` with:
    - the session results and the observation of task 1.3;
    - the checks of task 5.1;
    - ShellCheck and PSScriptAnalyzer, not required (no `*.sh` or `*.ps1`
      file changed), and unavailable in the session (no engine);
    - "Follow-up after closure: none", because no runtime code changed.

    Any environmental failure of the discovery is recorded with its cause.
  - **Verify:** the validation and the diff check pass, and the record has
    every entry listed above.
- [x] 5.3 Commit the reference branch with the subject `State that changes
  close in the working session` and the co-author trailer.
  - **Verify:** `git status --porcelain` is empty.

## Workflow follow-up

- The user reviews, pushes and merges the six branches.
- After the merge, archive the change in `sandbox-container`. This creates
  the main spec `change-validation` and updates `reference-propagation`.
  Verify the result with `openspec validate --specs --strict`.

## Follow-up after closure

- None. The change touches no runtime code, so no other environment has
  anything to verify.
