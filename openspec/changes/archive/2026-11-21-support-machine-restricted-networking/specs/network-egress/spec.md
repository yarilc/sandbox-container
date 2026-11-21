# Spec Delta

## ADDED Requirements

### Requirement: Restricted sessions run the application under a confined init
After confinement, the guard SHALL run the application as its child in a new process group that becomes the controlling terminal's foreground group, forward the termination and user signals it receives to the application, reap orphaned processes, and exit with the application's status, or 128 plus the signal number when a signal ended it. The waiting guard SHALL keep no proxy channel and no standard input or output.

#### Scenario: Interrupt from the terminal
- **WHEN** the user presses Ctrl+C during a restricted session whose command, such as `sleep 60`, installs no SIGINT handler
- **THEN** the command ends at once and the session's status is 130, as in an unrestricted session

#### Scenario: One interrupt
- **WHEN** the application handles SIGINT and the user presses Ctrl+C once
- **THEN** the application receives exactly one SIGINT

#### Scenario: Shutdown signal
- **WHEN** the launcher's bounded shutdown sends TERM to a restricted container
- **THEN** the application receives TERM before the forced removal

#### Scenario: Exit status and orphans
- **WHEN** the application starts a background process and exits with status 37
- **THEN** the session's status is 37 and the guard exits without waiting for the background process

#### Scenario: Confined supervisor
- **WHEN** the application runs
- **THEN** the waiting guard runs under the same Landlock and seccomp restrictions and holds neither the provider's proxy channel nor standard input and output
