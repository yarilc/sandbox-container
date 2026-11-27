# change-validation Specification

## Purpose

Define where a change in the sandbox family is verified and closed: only in the working session, with spikes on other environments while the change is designed and runs on other environments as follow-up after closure.

## Requirements

### Requirement: A started change closes in the working session
Once a change of the sandbox family is applied, its tasks SHALL be carried out and verified only in the working session, the environment where the agent works. No task SHALL wait for the operator or for another environment: the WSL host outside the session, a native Linux host, a Windows host or a real installation.

#### Scenario: Tasks of a new change
- **WHEN** a change's tasks are written
- **THEN** none asks the operator or another environment to run a check, and each verification names a command the working session can run

#### Scenario: Code with known lab-host differences
- **WHEN** a change modifies code whose runtime suites are known to behave differently on the Rocky 9 lab host
- **THEN** the tasks verify it with the session's checks, and the lab host run is listed in the follow-up after closure

### Requirement: Unavailable checks do not block closure
A check the working session cannot run, or one that fails because of the session's environment, SHALL be recorded in `docs/validation.md` with its reason and SHALL move to the follow-up after closure. It SHALL NOT block the change's closure. A failure caused by the change itself SHALL be fixed in the change.

#### Scenario: No engine in the session
- **WHEN** the session has no container engine and a task names a runtime mode
- **THEN** the record shows the mode as unavailable in the session with that reason, the mode is listed in the follow-up, and the task can be completed

#### Scenario: Failure from the session's environment
- **WHEN** a budget subtest fails because the session's engine applies no cgroup limits
- **THEN** the record names that cause, the subtest is listed in the follow-up, and the change can close

#### Scenario: Failure from the change
- **WHEN** a unit test fails because of the change's code
- **THEN** the change does not close until the test passes

### Requirement: Spikes only before a change starts
A check on another environment SHALL be allowed only as a spike, while a change is explored, proposed or designed, to answer one specific question. The design SHALL record the spike's question, environment, command and result. A spike SHALL NOT be a task.

#### Scenario: Spike during design
- **WHEN** a design needs to know whether the lab host's engine mounts `/dev` read-only for the runner's client
- **THEN** the spike runs before the tasks are written, and `design.md` records its question, host, command and result

#### Scenario: Question during the change
- **WHEN** a question that only another environment can answer arises after the change was applied
- **THEN** the question is listed in the follow-up after closure, and no task waits for its answer

### Requirement: Follow-up after closure
Runs on other environments SHALL come after the change closes. `tasks.md` SHALL list them as plain bullets under "Follow-up after closure", never as checkboxes. The validation record SHALL list each one as pending, and later its result. A defect they find SHALL be fixed by a new change; the closed change SHALL NOT be reopened.

#### Scenario: Windows check in the tasks
- **WHEN** a change needs a Windows PowerShell 5.1 check
- **THEN** it is a bullet under "Follow-up after closure" in `tasks.md`, and OpenSpec counts no open task for it

#### Scenario: Follow-up passes
- **WHEN** a follow-up run passes on the lab host
- **THEN** its result is added to the change's or the tag's section of `docs/validation.md`, and its pending entry is resolved

#### Scenario: Follow-up finds a defect
- **WHEN** a follow-up run finds a defect
- **THEN** a new change fixes it, and the closed change's artifacts are unchanged

### Requirement: Guidelines reach every agent
Each of the six repositories (`sandbox-container`, `claude-container`, `codex-container`, `opencode-container`, `pi-container`, `antigravity-container`) SHALL state this rule in `AGENTS.md`, in a section named "Change workflow and validation environments". Each SHALL have a `CLAUDE.md` that holds only the import `@AGENTS.md`.

#### Scenario: Claude session in a repository
- **WHEN** a Claude session works in one of the six repositories
- **THEN** it loads that repository's `AGENTS.md` through `CLAUDE.md`

#### Scenario: Guidelines edited
- **WHEN** a maintainer changes a repository's guidelines
- **THEN** only `AGENTS.md` changes, and `CLAUDE.md` still holds only `@AGENTS.md`

#### Scenario: No conflicting guideline
- **WHEN** a maintainer reads `AGENTS.md` in any of the six repositories
- **THEN** no line asks for another environment within a change, and the Windows PowerShell 5.1 check, sessions opened on other hosts and operator checks with real accounts are named as follow-up after closure
