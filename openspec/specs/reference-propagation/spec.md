# reference-propagation Specification

## Purpose

Propagate each new reference tag of the shared network and setup components from this repository to the sibling wrappers through a documented procedure and a verifying tool, so that every wrapper keeps byte-identical copies, an accurate reference manifest and an unchanged history record.

## Requirements

### Requirement: Documented propagation procedure
The repository SHALL document how a change to the shared components reaches the other wrappers: when a new `sandbox-ref-N` tag is needed, how to create it, how to adopt it in each wrapper, which suites to run, how to record the results, and how to update the five-wrapper parity table. A defect found during adoption SHALL be fixed in this repository first and published under a new tag; the other wrappers SHALL NOT carry a fork.

#### Scenario: Maintainer prepares a new reference
- **WHEN** a maintainer changes a shared file and reads the procedure
- **THEN** it states that the change needs a new annotated tag, lists the adoption steps for Claude, Codex, OpenCode, Pi and Antigravity, and names the tool that performs the mechanical part

#### Scenario: Adoption reveals a shared defect
- **WHEN** a wrapper's suites fail because of shared code during adoption
- **THEN** the procedure directs the fix to this repository under a new tag, followed by a new adoption, instead of an edit in the wrapper

### Requirement: Verified adoption preconditions
The propagation tool SHALL refuse to change a target checkout unless:
- its git tree is clean;
- its `tests/test_reference_copy.py` names the old tag and that tag's commit in this repository;
- both tags exist here;
- every file in the target's manifest equals the old tag.

Each refusal SHALL name the failed condition and change nothing.

#### Scenario: Target has local edits
- **WHEN** the target checkout has uncommitted changes
- **THEN** the tool exits nonzero naming the dirty tree and writes nothing

#### Scenario: Target is on another reference
- **WHEN** the target's manifest names a tag or commit different from the requested old tag
- **THEN** the tool exits nonzero naming both values and writes nothing

#### Scenario: Target carries a fork
- **WHEN** a copied file in the target differs from the old tag
- **THEN** the tool exits nonzero naming the file and writes nothing

### Requirement: Exact propagation within the adopted scope
The tool SHALL compute the shared files (as listed by the new tag's `tests/test_alignment.py`) modified, added or removed between the tags, limited to the target's adopted scope: its manifest files, additions under a directory it already adopts, and every file of a shared directory that the new tag introduces. A dry run SHALL only print the plan. An applied run SHALL write each file from the new tag byte for byte, delete removed files, and rewrite `REFERENCE_TAG`, `REFERENCE_COMMIT` and the manifest hashes.

#### Scenario: Dry run
- **WHEN** the tool runs without `--apply`
- **THEN** it prints the files to update, add and remove and the documents to touch, and the target is unchanged

#### Scenario: Applied adoption
- **WHEN** the tool runs with `--apply` on a valid target
- **THEN** it creates the branch `adopt-<new tag>`, the target's shared files equal the new tag, and the target's `tests/test_reference_copy.py` passes

#### Scenario: Partially adopted target
- **WHEN** a target has adopted `network/` but not yet `setup/common.py` and the new tag changes `setup/common.py`
- **THEN** the tool leaves `setup/common.py` absent and reports it as outside the adopted scope

#### Scenario: New shared directory
- **WHEN** the new tag adds the shared directory `launcher/` and the shared tests `tests/test_launcher.py` and `tests/fake_podman.py`
- **THEN** a target that adopts the old tag's shared tests receives all of them as additions

### Requirement: Current-state references only
An applied run SHALL replace the old tag and commit with the new ones only in current-state documents:
- every mention in the README, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`;
- the current references of `docs/network-contract.md`, as "Network contract references" defines them.

It SHALL NOT change `docs/validation.md`, `CHANGELOG.md`, `todo.md` or archived OpenSpec changes, which record history.

#### Scenario: Historical record keeps the old tag
- **WHEN** the target's validation record and changelog mention the old tag
- **THEN** those files are unchanged after the applied run, while the README and the network contract name the new tag

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

### Requirement: The reference repository is agent-neutral
`sandbox-container` SHALL be the only repository that edits the shared files, holds `tools/propagate.py` and `docs/propagation.md`, and creates `sandbox-ref-N` tags. Its tag history SHALL continue the earlier tags `sandbox-ref-1` to `sandbox-ref-18` with the same commits. Every agent wrapper, Claude included, SHALL adopt tags as a target of the tool.

#### Scenario: Adoption from a previous tag
- **WHEN** the tool runs from `sandbox-container` against a wrapper whose manifest names `sandbox-ref-18` and its commit
- **THEN** it resolves both from this repository and proposes the adoption of the requested new tag

#### Scenario: Claude is a target
- **WHEN** the maintainer reads the procedure or the tool's messages
- **THEN** they name `sandbox-container` as the reference and list Claude among the adopting wrappers

### Requirement: Shared mechanics tests use a fixed fixture profile
The shared test set SHALL include an agent-neutral fixture profile and policy with at least two authentication methods on synthetic `.test` hosts, an approval-bypass variable and an agent-variable prefix. Shared tests that exercise the shared modules SHALL use that fixture, never the checkout's profile. Tests that launch the checkout's wrapper SHALL be per-agent, except the qualification gate, which SHALL use the real profile.

#### Scenario: Provider mechanics in the reference
- **WHEN** the shared suite runs in `sandbox-container`, whose own profile declares no authentication method
- **THEN** provider policy, proxy and setup tests still run against the fixture profile and pass

#### Scenario: Same result in every wrapper
- **WHEN** an adopting wrapper runs the shared mechanics tests
- **THEN** the module-level tests read no value from that wrapper's profile

#### Scenario: Tests that launch the wrapper
- **WHEN** a test runs the checkout's wrapper for setup entry, questionnaire or managed-launch admission
- **THEN** it lives in the per-agent `tests/test_setup_wrapper.py`, outside the shared set, because wrappers differ in mode admission

#### Scenario: Qualification gate through the wrapper
- **WHEN** the shared qualification runtime tests run `--container-qualify` through the checkout's wrapper
- **THEN** they use the real profile and wrapper, because the gate behaves the same in every wrapper

#### Scenario: Production code never loads the fixture
- **WHEN** a launcher, setup or qualification command runs outside the test suites
- **THEN** it loads only the checkout's or installation's own `agent/profile.json`; no variable or argument selects the fixture

### Requirement: Shared suite validates the real profile
The shared test set SHALL include checks of the checkout's own profile and policy: schema validity, identifier coverage, distinct variable names, and, when the profile declares authentication methods, one policy profile per method with the declared hosts. Checks that need methods SHALL be skipped with a stated reason when the profile declares none.

#### Scenario: Reference profile without methods
- **WHEN** the real-profile checks run in `sandbox-container`
- **THEN** schema and identifier checks pass and method-to-policy checks are reported as skipped because no authentication method is declared

#### Scenario: Agent profile with a missing policy profile
- **WHEN** a wrapper's profile declares a method whose policy profile is absent from its policy file
- **THEN** the real-profile checks fail naming the method

### Requirement: Parity table names the reference
The parity table in `docs/network-contract.md` SHALL have a row for `sandbox-container` and one row for each wrapper, Claude included, identical in every repository. Its contract adoption cell SHALL read `Reference (sandbox-ref-N, ...)` with the latest tag in the reference row, and `Adopted sandbox-ref-N: ...` with the adopted tag in each wrapper row. The real enforcement cells SHALL name the tag each result ran at, and keep it when a later tag is adopted.

#### Scenario: Tag created
- **WHEN** `sandbox-ref-19` is created
- **THEN** the reference row names it, and each wrapper row names the tag that wrapper has adopted

#### Scenario: Results from an earlier tag
- **WHEN** a wrapper adopts a new tag, and its real enforcement cell records results from the previous tag
- **THEN** those results still name the previous tag, and results of the new tag are added beside them

### Requirement: Adopted manifest names the reference repository
An applied run SHALL make the target's `tests/test_reference_copy.py` name the repository the tool runs from: the sibling checkout path it compares against, its docstring and its skip message. The dry run SHALL report this manifest change. A manifest that already names the reference SHALL be left as it is.

#### Scenario: Manifest written while claude-container held the role
- **WHEN** the tool applies a new tag from `sandbox-container` to a wrapper whose manifest names `claude-container` as its sibling
- **THEN** the manifest names `sandbox-container` in its sibling path, docstring and skip message, and its sibling check compares against the `sandbox-container` checkout

#### Scenario: Sibling check after adoption
- **WHEN** the adopted wrapper's reference-copy test runs next to a `sandbox-container` checkout that has the new tag
- **THEN** the sibling check runs against that tag instead of being skipped

### Requirement: Shared tests do not read wrapper variable names
A shared test that uses an agent wrapper's runtime harness SHALL obtain the values it needs without naming that wrapper's variables, because the shared test sees only the fixture profile while the harness uses the wrapper's own names.

#### Scenario: Guarded multiplex in an agent wrapper
- **WHEN** `bash tests/run-runtime.sh --guard` runs in a wrapper whose network runtime harness returns `<PREFIX>_EGRESS_IMAGE`
- **THEN** the shared guarded-multiplex tests find the proxy image and pass, without a `KeyError`

#### Scenario: Ambiguous harness environment
- **WHEN** a harness environment contains no entry, or more than one entry, ending in `_EGRESS_IMAGE`
- **THEN** the shared test fails with a message naming the problem

### Requirement: Shared tests run the real image with its own profile
A shared test that runs a checkout's real agent image SHALL take every property of that image's layout, such as its native home, from the checkout's real profile, not from the fixture profile.

#### Scenario: Agent writes to its home at startup
- **WHEN** `bash tests/run-runtime.sh --guard` runs in a wrapper whose agent command creates directories under its native home
- **THEN** the guarded production-container test mounts that home writable and passes

#### Scenario: Reference checkout
- **WHEN** the same test runs in `sandbox-container`
- **THEN** it mounts the shell profile's home and passes

### Requirement: Network contract references
In `docs/network-contract.md`, an applied run SHALL replace only:
- the old tag where the reference line names it with the old commit;
- the old commit wherever it appears;
- the old tag in the parity table's contract adoption cell of the target's own row and of the reference row.

The target's own row SHALL be the row labeled with the `display_name` of the target's `agent/profile.json`. The dry run SHALL report the references it will replace and the old-tag mentions it keeps.

#### Scenario: Parity history keeps the old tag
- **WHEN** a real enforcement cell of the target's parity table records a result as `sandbox-ref-34 modes passed`, and the target adopts `sandbox-ref-35` from `sandbox-ref-34`
- **THEN** that cell still names `sandbox-ref-34` after the applied run, while the target's and the reference's contract adoption cells name `sandbox-ref-35`

#### Scenario: Other wrappers keep their adoption
- **WHEN** Codex adopts `sandbox-ref-35` from `sandbox-ref-28`, and the Antigravity row of its parity table reads `Adopted sandbox-ref-28`
- **THEN** the Antigravity row is unchanged after the applied run, and only the Codex row's contract adoption cell names `sandbox-ref-35`

#### Scenario: Reference line
- **WHEN** the target's network contract says that the shared components come from `sandbox-container` at the old tag, with its commit
- **THEN** after the applied run that line names the new tag and the new commit

#### Scenario: Dry run counts kept mentions
- **WHEN** the tool runs without `--apply` against a target whose network contract mentions the old tag in history entries
- **THEN** the documents line reports the references to replace and the mentions kept in the network contract, and the target is unchanged

### Requirement: Unreadable parity table is refused
When the target's network contract has a parity table, the tool SHALL refuse the target before writing anything if:
- its profile has no `display_name`;
- the table has no single row with that label;
- a row lacks the header's cells.

The refusal SHALL name the problem.

#### Scenario: Target without a parity row
- **WHEN** the target's network contract has a parity table without a row for its profile's `display_name`
- **THEN** the tool exits nonzero naming the missing row, and writes nothing

#### Scenario: Row with an extra cell
- **WHEN** a row of the target's parity table has more cells than the header
- **THEN** the tool exits nonzero naming the line, and writes nothing

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
- **WHEN** the range changes `tests/fake_podman.py`, and the target's `tests/test_launcher.py` names it
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
When the range adds or removes a shared file, the plan SHALL list each line of the target's own tracked files that names a shared file of the same directory, the added or removed one included, with path and line number. Shared files, the manifest, `docs/validation.md`, `CHANGELOG.md` and the target's `openspec/` directory SHALL be excluded. The warnings SHALL NOT block a dry or an applied run.

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
The procedure SHALL state that a wrapper validates an adoption in its working session: the checklist's commands the session can run and, for its own files changed in the adoption, the mode that runs them or its cases that exercise the change. The record SHALL list the commands not run, with the reference's record of the tag as their evidence. `tools/adoption-run.sh` on WSL or a native Linux host SHALL be follow-up after closure.

#### Scenario: Maintainer reads the verification step
- **WHEN** a maintainer reads the step of `docs/propagation.md` that verifies an adoption
- **THEN** it names the working session, the record of the commands not run, and the runner as follow-up after closure

#### Scenario: Wrapper test changed in the adoption
- **WHEN** an adoption changes the fixture setup of the wrapper's own `tests/test_network_runtime.py`
- **THEN** the validation runs at least one `--network` case that uses that setup in the session, or records it as unavailable there and lists it in the follow-up, and the record names it

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
