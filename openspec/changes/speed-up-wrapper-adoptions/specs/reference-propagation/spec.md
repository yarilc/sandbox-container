# Spec Delta

## ADDED Requirements

### Requirement: Checklist commands by changed component
The checklist SHALL always name the reference-copy and alignment tests. For the files changed between the tags, it SHALL add the commands that exercise them: the setup, qualification, guard, network and wrapper modes as before, plus the mappings of this requirement's scenarios. It SHALL name each command once, and drop a `-k` selection of a mode it already names in full.

#### Scenario: Launcher core changed
- **WHEN** the range changes `launcher/core.sh`
- **THEN** the checklist names `--wrapper` and the default runtime mode

#### Scenario: Engine inputs changed in a target with the engine cases
- **WHEN** the range changes `setup/engine.py` or a file under `launcher/engine/`, and the target's `tests/test_runtime.py` defines `SessionEngineTests` and its `tests/test_network_runtime.py` defines `test_offline_session_engine_has_no_external_path`
- **THEN** the checklist names `bash tests/run-runtime.sh -k SessionEngineTests` and `bash tests/run-runtime.sh --network -k test_offline_session_engine_has_no_external_path`, unless it names the full mode

#### Scenario: Engine inputs changed in a target without the engine cases
- **WHEN** the range changes `launcher/engine/Containerfile`, and the target's tests do not define those cases
- **THEN** the checklist names the full default runtime mode and the full `--network` mode

#### Scenario: Qualified file changed
- **WHEN** the range changes a file listed in the new tag's `SHARED_CODE`, such as `network/session.py`
- **THEN** the checklist names `--qualification`

#### Scenario: Shared test module without a runner mode
- **WHEN** the range changes `tests/test_engine.py` and `tests/test_toolchains.py`
- **THEN** the checklist's host unit command lists `tests.test_engine` and `tests.test_toolchains` beside the reference-copy and alignment tests

#### Scenario: Shared test helper changed
- **WHEN** the range changes `tests/fake_podman.py`, and the target's `tests/test_launcher.py` imports it
- **THEN** the checklist names `--wrapper`, the mode that runs `tests/test_launcher.py`

#### Scenario: Windows files changed
- **WHEN** the range changes a file under `launcher/windows/`
- **THEN** the checklist names a manual step: `tools/windows-validate.ps1` on a Windows host

#### Scenario: Claude's adoption of sandbox-ref-36
- **WHEN** the checklist is computed for `claude-container` from `sandbox-ref-35` to `sandbox-ref-36`
- **THEN** it names, in order, the host unit tests of `tests.test_reference_copy`, `tests.test_alignment`, `tests.test_engine` and `tests.test_toolchains`, then `--setup`, `--setup-runtime`, `--qualification`, `--wrapper`, the default runtime mode and `--network -k test_offline_session_engine_has_no_external_path`

### Requirement: Checklist of an adopted target
With `--checklist`, the tool SHALL print the checklist for a target whose manifest names the new tag and its commit. It SHALL print one line for each entry, with:
- a short name, its kind and its command;
- one line for each preparation, such as the engine image rebuild;
- one line for each manual step.

It SHALL write nothing and SHALL NOT require a clean tree. A target on another tag SHALL be refused.

#### Scenario: Runner input
- **WHEN** the tool runs with `--checklist` against a wrapper that adopted `sandbox-ref-36` from `sandbox-ref-35`
- **THEN** it prints one tab-separated line per entry, preparation and manual step, and the target is unchanged

#### Scenario: Target not yet adopted
- **WHEN** the tool runs with `--checklist` against a wrapper whose manifest names the old tag
- **THEN** it exits nonzero naming the manifest's tag, and prints no entry

### Requirement: Review warnings for listed shared files
When the range adds or removes a shared file, the plan SHALL list each line of the target's own tracked files that names another shared file of the same directory, with path and line number. Shared files, the manifest, `docs/validation.md`, `CHANGELOG.md` and the target's `openspec/` directory SHALL be excluded. The warnings SHALL NOT block a dry or an applied run.

#### Scenario: Hand-written list of engine inputs
- **WHEN** the range adds `launcher/engine/start.sh`, and the target's own `tests/test_network_runtime.py` names `launcher/engine/entrypoint.sh` on line 90
- **THEN** the dry run lists `tests/test_network_runtime.py:90` for review, and the run completes

#### Scenario: Range without additions or removals
- **WHEN** the range only modifies shared files
- **THEN** the plan lists no review warning

### Requirement: Reference changes of the range
The plan SHALL list each OpenSpec change of this repository whose directory a commit between the tags touched. For each change it SHALL give:
- its location at this checkout's `HEAD`, archived or active;
- its delta spec files;
- the capabilities among them that have no main spec in the target.

#### Scenario: Changes archived after the tag
- **WHEN** the range from `sandbox-ref-35` to `sandbox-ref-36` holds `support-nested-systemd-containers` and `declare-engine-image-capabilities`, and both were archived later
- **THEN** the plan lists both with their archive directories and their `session-container-engine` deltas

#### Scenario: Reference-only capability
- **WHEN** a change of the range has a delta for `reference-propagation`, which the target has no main spec for
- **THEN** the plan marks that delta as not in the target

#### Scenario: Change still active
- **WHEN** a change of the range is still active at `HEAD`
- **THEN** the plan lists it as active

### Requirement: Adoption validation perimeter
The procedure SHALL state that a wrapper validates an adoption on one native host, with `tools/adoption-run.sh` running the checklist's commands. For its own files changed in the adoption, the wrapper SHALL also run the mode that runs them, or the cases of it that exercise the change. The record SHALL list the commands not run, with the reference's runs as their evidence.

#### Scenario: Maintainer reads the verification step
- **WHEN** a maintainer reads the step of `docs/propagation.md` that verifies an adoption
- **THEN** it names the runner, the single host and the record of the commands not run

#### Scenario: Wrapper test changed in the adoption
- **WHEN** an adoption changes the fixture setup of the wrapper's own `tests/test_network_runtime.py`
- **THEN** the validation runs at least one `--network` case that uses that setup, and the record names it

## MODIFIED Requirements

### Requirement: Verification checklist after adoption
After a run, the tool SHALL print the commands to execute in the target, ready to run: runner modes that its `tests/run-runtime.sh` offers, `-k` selections of them and host unit tests, as "Checklist commands by changed component" defines. Host unit tests SHALL run with `SANDBOX_TEST_TMPDIR` on private storage. The tool SHALL also print a validation-record template with one row per command, and a commit message. It SHALL NOT run the suites, commit, merge or push.

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
Before a new `sandbox-ref-N` tag is created, this repository SHALL pass, on WSL and on a native Linux host, every runner mode that the checklist names for the shared files changed since the previous tag, in full and without `-k` selections. It SHALL also pass the qualification mode whenever a changed file is digested by qualification. The record SHALL give each mode's result per host, or record it as unavailable. No tag SHALL be created while a listed mode fails.

#### Scenario: Qualification inputs changed
- **WHEN** a change modifies a file that qualification digests, such as the qualification records or a setup module listed as shared code
- **THEN** `bash tests/run-runtime.sh --qualification` passes in this repository before the tag is created, and the validation record shows its result

#### Scenario: Shared test fixture misses a new shared file
- **WHEN** a change adds a file to the shared code digested by qualification, and a shared runtime fixture builds an installation without it
- **THEN** the reference's qualification mode fails before tagging, and the defect is fixed before any wrapper adopts the tag

#### Scenario: Both native hosts
- **WHEN** the checklist for a new tag names `--network -k test_offline_session_engine_has_no_external_path`
- **THEN** the reference runs the whole `--network` mode on WSL and on the native Linux host before tagging, and records both results

#### Scenario: Procedure states the rule
- **WHEN** a maintainer reads the step that prepares a new tag in `docs/propagation.md`
- **THEN** it names the checklist that `tools/propagate.py` prints as the minimum set of reference runner modes, the qualification rule and the two hosts
