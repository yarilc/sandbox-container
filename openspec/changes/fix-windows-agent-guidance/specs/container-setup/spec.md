# Spec Delta

## MODIFIED Requirements

### Requirement: Setup started by the Windows entry
When the Windows entry starts setup, setup SHALL omit the shell `PATH` guidance and the managed-command lines for launching and reviewing setup from its plan and summary, and SHALL state that the Windows entry starts sessions. Its pending authentication steps SHALL name `<name>.ps1` and PowerShell's `$env:`, not the managed command. Setup started from a Linux shell SHALL keep that guidance.

#### Scenario: Setup from the Windows entry
- **WHEN** the user runs `<name>.ps1 --container-setup`, or `--container-install` runs setup from the installed copy
- **THEN** the setup output contains no `export PATH=` line, no shell startup file and no distribution path of the managed command, and the entry then prints how to start sessions

#### Scenario: Login postponed from the Windows entry
- **WHEN** setup started by the Windows entry selects a method with login arguments and the user declines the login
- **THEN** the next authentication action is `<name>.ps1` followed by the login arguments, with no distribution path

#### Scenario: API key method from the Windows entry
- **WHEN** setup started by the Windows entry selects a method with a credential variable `<KEY>`
- **THEN** it says to set `$env:<KEY>` in PowerShell before running `<name>.ps1`

#### Scenario: Setup from a Linux shell
- **WHEN** setup runs from a Linux shell whose `PATH` lacks the managed command directory
- **THEN** it prints the `export PATH=` guidance and the managed-command lines as before
