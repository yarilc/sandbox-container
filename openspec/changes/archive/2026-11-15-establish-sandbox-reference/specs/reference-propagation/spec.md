# Spec Delta

## MODIFIED Requirements

### Requirement: Documented propagation procedure
The repository SHALL document how a change to the shared components reaches the other wrappers: when a new `sandbox-ref-N` tag is needed, how to create it, how to adopt it in each wrapper, which suites to run, how to record the results, and how to update the five-wrapper parity table. A defect found during adoption SHALL be fixed in this repository first and published under a new tag; the other wrappers SHALL NOT carry a fork.

#### Scenario: Maintainer prepares a new reference
- **WHEN** a maintainer changes a shared file and reads the procedure
- **THEN** it states that the change needs a new annotated tag, lists the adoption steps for Claude, Codex, OpenCode, Pi and Antigravity, and names the tool that performs the mechanical part

#### Scenario: Adoption reveals a shared defect
- **WHEN** a wrapper's suites fail because of shared code during adoption
- **THEN** the procedure directs the fix to this repository under a new tag, followed by a new adoption, instead of an edit in the wrapper

## ADDED Requirements

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
