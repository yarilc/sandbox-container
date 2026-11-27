# Proposal

## Why

Changes in the sandbox family stay open for hours or days, waiting for other
environments:
- **Operator tasks:** tasks ask the operator to run suites on the Rocky 9 lab
  host, on the WSL host outside the session, or on Windows. Examples are
  `fix-runtime-test-portability` 4.2, `replace-podman-delegation-with-session-engine`
  8.2 and 8.3, and `support-nested-systemd-containers` 5.1 and 5.2.
- **Round trips:** each of those runs costs a round trip of commands and log
  archives. About twenty archives were exchanged for `sandbox-ref-35` and
  `sandbox-ref-36` alone.
- **The contracts require it:**
  - `reference-propagation` requires every checklist mode on WSL and on a
    native Linux host before a tag;
  - it requires an adoption to be validated on one native host;
  - the guidelines ask for a Windows host and for interactive sessions on
    other hosts.
- **Claude does not see the guidelines:** Claude Code loads `CLAUDE.md`, and
  no repository has one, so `AGENTS.md` does not reach the agent that does
  most changes.

A started change should finish where it is developed. Other environments
should verify it afterwards.

## What Changes

- **New rule for every change (new capability `change-validation`):**
  - **During the change:** once a change is applied, its tasks are carried
    out and verified only in the working session, the environment where the
    agent works. No task waits for the operator or for another environment.
  - **Unavailable checks:** a check the session cannot run, or one that fails
    because of the session's environment, is recorded with its reason. It
    moves to the follow-up and does not block closure.
  - **Spikes:** a spike on another environment is allowed only while a
    change is explored, proposed or designed, to answer one specific
    question. The design records it; it is never a task.
  - **After closure:** runs on other environments come after closure:
    - runner modes on WSL and on the native Linux host;
    - `tools/adoption-run.sh`;
    - `tools/windows-validate.ps1` on Windows PowerShell 5.1;
    - operator checks with real accounts.

    `tasks.md` lists them as plain bullets under "Follow-up after closure",
    and the validation record lists them as pending. A defect they find
    opens a new change.
- **`AGENTS.md` in the six repositories:**
  - a new section "Change workflow and validation environments" states the
    rule;
  - lines that ask for another environment inside a change are reworded as
    follow-up:
    - the Windows PowerShell 5.1 host check;
    - the interactive session "opened on that host";
    - the one-host adoption run;
    - Antigravity's operator-run authenticated checks.
- **`CLAUDE.md` in the six repositories:** one line, `@AGENTS.md`, so Claude
  sessions load the same guidelines. `AGENTS.md` states that `CLAUDE.md`
  holds nothing else.
- **Tag gate (`reference-propagation`):**
  - a `sandbox-ref-N` tag is created when its change closes in the session,
    after the checklist checks the session supports;
  - the full modes on WSL and on the native Linux host follow the tag, and
    are recorded under the tag's section;
  - a shared defect they find is fixed by a new change under a new tag.
- **Adoption perimeter (`reference-propagation`):**
  - a wrapper validates an adoption in its working session;
  - `tools/adoption-run.sh` on a host becomes the follow-up after closure.
- **Propagation report (`tools/propagate.py`):**
  - the report prints "Run in the session" and a "Follow-up after closure"
    list with the runner line and the manual steps;
  - the record template keeps the session checks in its table and lists the
    follow-up as pending;
  - the report prints a follow-up block ready for `tasks.md`.

  The `--checklist` output, which `tools/adoption-run.sh` reads, is
  unchanged.
- **Documents:** `docs/propagation.md` (steps 1 and 3) and the `README.md`
  paragraph on the runner follow the new gate and perimeter.

## Capabilities

### New Capabilities

- `change-validation`: where a change in the sandbox family is verified and
  closed. It covers:
  - the working session as the only environment of a started change;
  - spikes during design;
  - the follow-up after closure and the shape of its record;
  - the guidelines file that every agent loads (`AGENTS.md`, imported by
    `CLAUDE.md`).

### Modified Capabilities

- `reference-propagation`:
  - "Reference runs the adoption suites before tagging": session checks
    before the tag, both native hosts after it;
  - "Adoption validation perimeter": the working session instead of one
    native host;
  - "Verification checklist after adoption": the report and the template
    separate the session checks from the follow-up.

## Impact

- **Reference files:**
  - `AGENTS.md` and a new `CLAUDE.md`;
  - `docs/propagation.md` and `README.md`;
  - `tools/propagate.py` (report only) and `tests/test_propagate.py`;
  - the `## Purpose` of `openspec/specs/adoption-runner/spec.md`;
  - `docs/validation.md` (this change's record).
- **No new tag:** no shared file under `network/`, `setup/` or `launcher/`
  changes, and no shared test changes. `tools/adoption-run.sh` and the
  `--checklist` lines are unchanged.
- **Wrappers:** `AGENTS.md` and a new `CLAUDE.md` in `claude-container`,
  `codex-container`, `opencode-container`, `pi-container` and
  `antigravity-container`. Each wrapper gets one branch and commit. There is
  no OpenSpec change and no spec delta in the wrappers: their `shared-launcher`
  requirement on Windows PowerShell 5.1 already allows a check after the
  release.
- **Operators:** fewer round trips during a change. Host and Windows runs are
  collected after closure, from the follow-up lists.
- **Risk:** a tag can reach the wrappers before the native hosts have run it.
  A defect found there needs a new tag and a new adoption.
