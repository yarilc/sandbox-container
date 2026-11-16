# Spec Delta

## ADDED Requirements

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
