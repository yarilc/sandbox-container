# Spec Delta

## ADDED Requirements

### Requirement: Shared tests run the real image with its own profile
A shared test that runs a checkout's real agent image SHALL take every property of that image's layout, such as its native home, from the checkout's real profile, not from the fixture profile.

#### Scenario: Agent writes to its home at startup
- **WHEN** `bash tests/run-runtime.sh --guard` runs in a wrapper whose agent command creates directories under its native home
- **THEN** the guarded production-container test mounts that home writable and passes

#### Scenario: Reference checkout
- **WHEN** the same test runs in `sandbox-container`
- **THEN** it mounts the shell profile's home and passes
