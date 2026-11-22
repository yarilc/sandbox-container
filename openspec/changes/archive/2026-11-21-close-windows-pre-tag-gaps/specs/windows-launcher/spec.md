# Spec Delta

## MODIFIED Requirements

### Requirement: Environment forwarded by name to the distribution
The entry SHALL forward to the launcher in the distribution, with unchanged values: validly named `<P>_*` variables except `<P>_WSL_*`; the profile's configuration-directory variable holding a distribution path; its approval-bypass and credential variables; and the names in `<P>_ENV_VARS`. It SHALL forward no other Windows variable, ignore the user's `WSLENV`, never forward a name the distribution environment depends on, and leave the PowerShell session's environment as it was.

#### Scenario: Launch settings from PowerShell
- **WHEN** `$env:<P>_MEMORY_LIMIT='2g'` is set in PowerShell
- **THEN** the launcher in the distribution receives `<P>_MEMORY_LIMIT=2g`

#### Scenario: Listed variable
- **WHEN** `<P>_ENV_VARS` is `GH_TOKEN` and `GH_TOKEN` is set in PowerShell
- **THEN** the session receives `GH_TOKEN` by name under the launcher's forwarding rules

#### Scenario: Name reserved by the distribution
- **WHEN** `<P>_ENV_VARS` lists `PATH`
- **THEN** the entry does not forward it and prints one notice naming it

#### Scenario: Credential variable of an authentication method
- **WHEN** the profile's API method declares `credential_env` `<KEY>`, `<KEY>` is set in PowerShell, and the user launches a provider session that uses that method
- **THEN** the launcher in the distribution receives `<KEY>` with its value, and the session receives it as on Linux

#### Scenario: Credential variable not set
- **WHEN** `<KEY>` is unset or empty in PowerShell
- **THEN** the entry does not forward it

#### Scenario: Unrelated Windows variable
- **WHEN** `USERPROFILE` is set and not listed
- **THEN** the distribution does not receive it

#### Scenario: Session environment restored
- **WHEN** the launch ends, successfully or not
- **THEN** `WSLENV` and every variable the entry set have their previous values in the PowerShell session

#### Scenario: Name that would split WSLENV
- **WHEN** a Windows variable named `<P>_X:BASH_ENV/u` is set
- **THEN** the entry does not forward it, prints a notice naming it, and `BASH_ENV` does not reach the distribution

#### Scenario: Windows path in the configuration-directory variable
- **WHEN** the profile's configuration-directory variable holds a Windows path, such as one set for the native agent
- **THEN** the entry does not forward it and prints a notice, so the configuration directory saved by setup applies
