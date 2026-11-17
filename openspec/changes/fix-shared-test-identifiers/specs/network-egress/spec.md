# Spec Delta

## MODIFIED Requirements

### Requirement: Agent-neutral shared sandbox components
The shared network sandbox, setup and launcher components, the shared tests and the compiled guard SHALL contain no agent-specific identifiers. That covers the identifiers the checkout's own profile declares and those of every sibling wrapper checkout found next to it. In-container paths, the guard binary name and the multiplex protocol marker SHALL be agent-neutral. Host-visible images, labels, variables and installation paths SHALL stay per-agent, as declared by the profile.

#### Scenario: Shared components contain an agent identifier
- **WHEN** a shared file contains an agent-specific identifier declared by the profile, outside the documented allow-list
- **THEN** the alignment test fails

#### Scenario: Shared components contain a sibling wrapper's identifier
- **WHEN** the reference checkout has wrapper checkouts next to it, and a shared file contains an identifier one of their profiles declares
- **THEN** the alignment test fails naming the file and line
- **AND** without sibling checkouts the test is skipped with a reason, and the own-profile check still runs

#### Scenario: Two wrappers on the same host
- **WHEN** two wrappers using different profiles run restricted sessions or qualification concurrently
- **THEN** each creates, inspects and cleans up only resources carrying its own profile's labels and image names

#### Scenario: Unchanged operator interface
- **WHEN** an existing user runs the wrapper with the same environment variables, images and saved setup preferences after requalification
- **THEN** modes, profiles, hosts, defaults, hardening and diagnostics behave as before the change
