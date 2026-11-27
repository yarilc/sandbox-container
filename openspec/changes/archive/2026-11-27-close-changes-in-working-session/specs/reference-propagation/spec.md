# Spec Delta

## MODIFIED Requirements

### Requirement: Verification checklist after adoption
After a run, the tool SHALL print the commands to run in the target's working session, ready to run: runner modes that its `tests/run-runtime.sh` offers, `-k` selections of them and host unit tests, as "Checklist commands by changed component" defines. Host unit tests SHALL run with `SANDBOX_TEST_TMPDIR` on private storage. The tool SHALL also print the follow-up after closure, a validation-record template and a commit message. It SHALL NOT run the suites, commit, merge or push.

#### Scenario: Setup files changed
- **WHEN** the propagated files include `setup/setup.py`
- **THEN** the checklist names the target's `--setup` mode, and `--setup-runtime` when the target offers it

#### Scenario: Two modes in one runner condition
- **WHEN** the target's `tests/run-runtime.sh` offers `--guard` as `[[ "${1:-}" == --guard || "${1:-}" == --guard-idle ]]` and the propagated files include `network/guard.c`
- **THEN** the checklist names the target's `--guard` mode

#### Scenario: Host unit tests carry private storage
- **WHEN** the checklist names host unit tests
- **THEN** their printed command sets `SANDBOX_TEST_TMPDIR` to a private directory

#### Scenario: No version-control side effects
- **WHEN** an applied run finishes
- **THEN** the target has an uncommitted working tree on `adopt-<new tag>`, and no commit, merge, tag or push was made

### Requirement: Reference runs the adoption suites before tagging
Before a new `sandbox-ref-N` tag is created, this repository SHALL pass in its working session every checklist mode for the shared files changed since the previous tag that the session can run, in full and without `-k` selections, and the qualification mode whenever a changed file is digested by qualification. A mode the session cannot run SHALL be recorded as unavailable with its reason. No tag SHALL be created while a mode run there fails because of the change.

#### Scenario: Qualification inputs changed
- **WHEN** a change modifies a file that qualification digests, such as the qualification records or a setup module listed as shared code
- **THEN** `bash tests/run-runtime.sh --qualification` passes in the working session before the tag is created, or is recorded as unavailable there with its reason, and the validation record shows the result

#### Scenario: Shared test fixture misses a new shared file
- **WHEN** a change adds a file to the shared code digested by qualification, and a shared runtime fixture builds an installation without it
- **THEN** the reference's qualification mode fails: in the session, the change fixes the defect before the tag; on a native host after the tag, a new change fixes it under a new tag

#### Scenario: Both native hosts
- **WHEN** the checklist for a new tag names `--network -k test_offline_session_engine_has_no_external_path` and the session can run `--network`
- **THEN** the reference runs the whole `--network` mode in the session before tagging, and on WSL and on the native Linux host after the tag as follow-up, and records each result

#### Scenario: Session without an engine
- **WHEN** the working session has no container engine and the checklist names `--network`
- **THEN** the record shows `--network` as unavailable in the session with that reason, the tag can be created, and the follow-up lists `--network` on both native hosts

#### Scenario: Procedure states the rule
- **WHEN** a maintainer reads the step that prepares a new tag in `docs/propagation.md`
- **THEN** it names the checklist that `tools/propagate.py` prints as the minimum set of reference runner modes, the qualification rule, the working session, and the runs on the two native hosts after the tag

### Requirement: Adoption validation perimeter
The procedure SHALL state that a wrapper validates an adoption in its working session: the checklist's commands the session can run and, for its own files changed in the adoption, the mode that runs them or its cases that exercise the change. The record SHALL list the commands not run, with the reference's record of the tag as their evidence. `tools/adoption-run.sh` on WSL or a native Linux host SHALL be follow-up after closure.

#### Scenario: Maintainer reads the verification step
- **WHEN** a maintainer reads the step of `docs/propagation.md` that verifies an adoption
- **THEN** it names the working session, the record of the commands not run, and the runner as follow-up after closure

#### Scenario: Wrapper test changed in the adoption
- **WHEN** an adoption changes the fixture setup of the wrapper's own `tests/test_network_runtime.py`
- **THEN** the validation runs at least one `--network` case that uses that setup in the session, or records it as unavailable there and lists it in the follow-up, and the record names it

## ADDED Requirements

### Requirement: Native hosts verify a tag after it is created
After a `sandbox-ref-N` tag is created, the checklist modes of its range SHALL run in full on WSL and on a native Linux host as follow-up, and the record SHALL give each mode's result per host under the tag's section. A failure caused by shared code SHALL be fixed by a new change under a new tag. Adoptions of the tag SHALL NOT wait for these runs.

#### Scenario: Host results under the tag's section
- **WHEN** the checklist for a tag names `--network -k test_offline_session_engine_has_no_external_path`
- **THEN** the follow-up runs the whole `--network` mode on WSL and on the native Linux host, and the tag's section records both results

#### Scenario: Shared defect found after the tag
- **WHEN** a follow-up run on the native Linux host fails because of shared code
- **THEN** a new reference change fixes it under a new tag, and the wrappers adopt that tag

#### Scenario: Adoption before the host runs
- **WHEN** a wrapper adopts a tag whose follow-up runs are still pending
- **THEN** the adoption proceeds, and its record cites the tag's pending follow-up

### Requirement: Report separates the follow-up after closure
The report SHALL list the follow-up after closure apart from the session commands: the `tools/adoption-run.sh` line for WSL or a native Linux host and every manual step. The record template SHALL have one table row per session command and list each follow-up entry as pending. The report SHALL also print the follow-up as plain bullets for `tasks.md`, without checkboxes.

#### Scenario: Windows step is follow-up
- **WHEN** the range changes a file under `launcher/windows/`
- **THEN** the Windows validation step is listed under "Follow-up after closure" with the runner line, the template's table has no row for it, and the template lists it as pending

#### Scenario: Follow-up block for the tasks
- **WHEN** the report is printed
- **THEN** it holds a "Follow-up after closure" block of plain bullets that names the runner line and each manual step, ready to paste into `tasks.md`

#### Scenario: Checklist lines for the runner
- **WHEN** the tool prints `--checklist` for an adopted target
- **THEN** each line still gives the kind, the name and the command, and a manual step keeps the kind `manual`
