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
The tool SHALL compute the shared files (as listed by the new tag's `tests/test_alignment.py`) modified, added or removed between the tags, limited to the target's adopted scope: its manifest files and additions under a directory it already adopts. A dry run SHALL only print the plan. An applied run SHALL write each file from the new tag byte for byte, delete removed files, and rewrite `REFERENCE_TAG`, `REFERENCE_COMMIT` and the manifest hashes.

#### Scenario: Dry run
- **WHEN** the tool runs without `--apply`
- **THEN** it prints the files to update, add and remove and the documents to touch, and the target is unchanged

#### Scenario: Applied adoption
- **WHEN** the tool runs with `--apply` on a valid target
- **THEN** it creates the branch `adopt-<new tag>`, the target's shared files equal the new tag, and the target's `tests/test_reference_copy.py` passes

#### Scenario: Partially adopted target
- **WHEN** a target has adopted `network/` but not yet `setup/common.py` and the new tag changes `setup/common.py`
- **THEN** the tool leaves `setup/common.py` absent and reports it as outside the adopted scope

### Requirement: Current-state references only
An applied run SHALL replace the old tag and commit with the new ones only in current-state documents:
- the README, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`;
- the reference line and the `Ported from` and `Reference` parity cells of `docs/network-contract.md`.

It SHALL NOT change `docs/validation.md`, `CHANGELOG.md`, `todo.md` or archived OpenSpec changes, which record history.

#### Scenario: Historical record keeps the old tag
- **WHEN** the target's validation record and changelog mention the old tag
- **THEN** those files are unchanged after the applied run, while the README and the network contract name the new tag

### Requirement: Verification checklist after adoption
After a run, the tool SHALL print the target runner modes to execute (from those its `tests/run-runtime.sh` offers): always the shared suite and the reference-copy check, plus the setup, qualification, network and guard modes when files they exercise changed. It SHALL also print a validation-record template and a commit message. It SHALL NOT run the suites, commit, merge or push.

#### Scenario: Setup files changed
- **WHEN** the propagated files include `setup/setup.py`
- **THEN** the checklist names the target's `--setup` mode, and `--setup-runtime` when the target offers it

#### Scenario: No version-control side effects
- **WHEN** an applied run finishes
- **THEN** the target has an uncommitted working tree on `adopt-<new tag>`, and no commit, merge, tag or push was made

### Requirement: Reference runs the adoption suites before tagging
Before a new `sandbox-ref-N` tag is created, this repository SHALL pass every runner mode that the propagation checklist names for the shared files changed since the previous tag, plus the qualification mode whenever a changed file is digested by qualification. The validation record for the tag SHALL list each of these modes with its result. A mode that cannot run SHALL be recorded as unavailable, and the tag SHALL NOT be created while a listed mode fails.

#### Scenario: Qualification inputs changed
- **WHEN** a change modifies a file that qualification digests, such as the qualification records or a setup module listed as shared code
- **THEN** `bash tests/run-runtime.sh --qualification` passes in this repository before the tag is created, and the validation record shows its result

#### Scenario: Shared test fixture misses a new shared file
- **WHEN** a change adds a file to the shared code digested by qualification, and a shared runtime fixture builds an installation without it
- **THEN** the reference's qualification mode fails before tagging, and the defect is fixed before any wrapper adopts the tag

#### Scenario: Procedure states the rule
- **WHEN** a maintainer reads the step that prepares a new tag in `docs/propagation.md`
- **THEN** it names the checklist that `tools/propagate.py` prints as the minimum set of reference runner modes, and the qualification rule

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
The five-wrapper parity table in `docs/network-contract.md` SHALL include a row for `sandbox-container` with `Reference (sandbox-ref-N)`, and every wrapper row, Claude included, SHALL read `Ported from sandbox-ref-N`.

#### Scenario: Tag created
- **WHEN** `sandbox-ref-19` is created
- **THEN** the reference row names it and the five wrapper rows name `Ported from` the tag they have adopted

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
