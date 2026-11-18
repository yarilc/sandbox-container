## ADDED Requirements

### Requirement: Launcher files pass ShellCheck
`launcher/core.sh`, the launcher fixtures and every `agent/launcher.sh` SHALL pass ShellCheck at warning level when each file is checked alone. Each SHALL declare its shell with a `shell=bash` directive. A suppressed finding SHALL be limited to the data and state the core shares with the agent part, or to a variable assigned indirectly, and SHALL carry a comment naming the reason. The reference SHALL provide a ShellCheck check, with a pinned ShellCheck version, that runs on any checkout.

#### Scenario: Shared files checked alone
- **WHEN** the reference check runs on a reference or wrapper checkout at warning level
- **THEN** it reports no finding for `launcher/core.sh`, `tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh` or `agent/launcher.sh`

#### Scenario: New finding in the core
- **WHEN** a change to `launcher/core.sh` introduces a ShellCheck warning
- **THEN** the reference check fails naming the file and line

#### Scenario: Lint-only edits keep behavior
- **WHEN** the directives and quoting are added
- **THEN** the shared launcher tests pass unchanged
