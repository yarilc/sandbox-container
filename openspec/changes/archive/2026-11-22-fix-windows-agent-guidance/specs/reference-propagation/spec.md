# Spec Delta

## MODIFIED Requirements

### Requirement: Verification checklist after adoption
After a run, the tool SHALL print the target runner modes to execute (from those its `tests/run-runtime.sh` offers): always the shared suite and the reference-copy check, plus the setup, qualification, network and guard modes when files they exercise changed. It SHALL also print a validation-record template and a commit message. It SHALL NOT run the suites, commit, merge or push.

#### Scenario: Setup files changed
- **WHEN** the propagated files include `setup/setup.py`
- **THEN** the checklist names the target's `--setup` mode, and `--setup-runtime` when the target offers it

#### Scenario: Two modes in one runner condition
- **WHEN** the target's `tests/run-runtime.sh` offers `--guard` as `[[ "${1:-}" == --guard || "${1:-}" == --guard-idle ]]` and the propagated files include `network/guard.c`
- **THEN** the checklist names the target's `--guard` mode

#### Scenario: No version-control side effects
- **WHEN** an applied run finishes
- **THEN** the target has an uncommitted working tree on `adopt-<new tag>`, and no commit, merge, tag or push was made
