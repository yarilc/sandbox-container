# shared-launcher Specification

## Purpose
Defines how every wrapper's launcher is built from one shared Bash core and a small agent part, so launcher behavior is specified, fixed and tested once for all wrappers.

## Requirements

### Requirement: One shared launcher core
Every wrapper SHALL run through the same shared Bash launcher core, `launcher/core.sh`, copied byte for byte from the reference tag and recorded in the reference-copy manifest like the other shared files. The core SHALL contain no agent identifiers and SHALL require no host tool beyond Podman, GNU coreutils and, for restricted modes, setup, qualification and the toolchain library, host Python 3.

#### Scenario: Core edited in a wrapper
- **WHEN** a wrapper's `launcher/core.sh` differs from the reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Unrestricted session without host Python
- **WHEN** an unrestricted session with the toolchain library disabled starts on a host without Python
- **THEN** the core launches it, and only the optional diagnostics filter is skipped

### Requirement: Thin wrapper entry script
Each wrapper's `<wrapper>-container.sh` SHALL only set the shell options, keep the invoked path, locate its directory with GNU `readlink -f` or, when readlink is missing, with the invoked path's directory, and source the core with the wrapper's `agent/launcher.sh` and its arguments. A missing readlink SHALL be reported by the core in the same order as other host-tool prerequisites, so help and setup guidance still work without it.

#### Scenario: Comparing two wrappers
- **WHEN** the entry scripts of two wrappers are compared after replacing the wrapper name
- **THEN** they are identical

#### Scenario: Help without readlink
- **WHEN** `--container-help` runs on a host without readlink, Podman or timeout
- **THEN** the help is printed and the exit status is 0

### Requirement: Agent launcher part consistent with the profile
Each wrapper SHALL provide `agent/launcher.sh` with plain assignments of the profile values the core needs, the agent's fixed session settings by scope (always, restricted, provider), unset and reserved variable names, and its hooks. The profile values SHALL equal `agent/profile.json` and `agent/policies/default.json`, checked by a credential-free test.

#### Scenario: Profile and launcher part disagree
- **WHEN** `agent/launcher.sh` and `agent/profile.json` declare different values for the same property
- **THEN** the alignment test fails naming the property

#### Scenario: Credentials follow the default policy
- **WHEN** the default policy declares a policy profile whose authentication method has a credential variable
- **THEN** `AGENT_CREDENTIALS` lists that profile with that variable, and the alignment test fails if it does not

### Requirement: Common launcher interface
Every wrapper SHALL accept the same `--container-*` options and `<P>_*` variables with the same meaning and defaults, as defined by the core, where `<P>` is the profile's variable prefix. The default network mode SHALL be `provider` for a profile with authentication methods and `offline` otherwise. A profile whose command is a shell SHALL always run in shell mode. Agent-specific variables SHALL be read only by agent hooks and SHALL appear in `--container-help` after the common ones.

#### Scenario: Agent profile without a mode
- **WHEN** a wrapper whose profile has authentication methods starts without `<P>_NETWORK` and without provider settings
- **THEN** it selects `provider`, stops with setup guidance, and performs no engine or state operation

#### Scenario: Shell profile
- **WHEN** the reference starts with or without `--container-shell`
- **THEN** it runs `/bin/bash` with the arguments in both cases

### Requirement: Bounded agent hooks
The core SHALL call agent code only through the documented hooks `agent_help`, `agent_validate`, `agent_approval_bypass`, `agent_command_args`, `agent_environment`, `agent_mounts` and `agent_build_args`, each at its documented point. A missing hook SHALL fall back to the core default. The core SHALL refuse a hook output outside its contract and SHALL stop with the hook's name when a hook fails. No hook SHALL run during shutdown.

#### Scenario: Agent part without hooks
- **WHEN** `agent/launcher.sh` defines none of the hooks
- **THEN** the session runs with the core's default behavior

#### Scenario: Hooks never see session identity
- **WHEN** the fixture agent part records the variables visible to each hook
- **THEN** none contains the session token or the container ID

#### Scenario: Hook output outside its contract
- **WHEN** a hook returns a writable bind, a mount over `/tmp`, `/run`, the workspace, the home or another mount, a malformed tmpfs size, or a variable name the core sets
- **THEN** the core refuses to start the session and names the hook

### Requirement: Shared launcher tests
The core SHALL be tested by `tests/test_launcher.py` with the shared fake engine `tests/fake_podman.py`, both copied unchanged into every wrapper. The tests SHALL run the core through the thin entry script with a fixture agent part that defines every hook and one that defines none. A wrapper's own launcher tests SHALL cover only its hooks, its agent data and its real image.

#### Scenario: Lifecycle defect fixed once
- **WHEN** a lifecycle defect is fixed in the reference core together with a shared test
- **THEN** every wrapper that adopts the tag receives both without editing its own files

#### Scenario: Unknown fake engine command
- **WHEN** the core issues an engine command the shared fake does not implement
- **THEN** the fake fails the test instead of succeeding silently

### Requirement: Launcher files pass ShellCheck
`launcher/core.sh`, `launcher/windows/bootstrap.sh`, the launcher fixtures and every `agent/launcher.sh` SHALL each pass ShellCheck alone, at warning level. Each SHALL declare its shell with a `shell=bash` directive. A suppressed finding SHALL concern only data and state the core shares with the agent part, or an indirectly assigned variable, and SHALL carry a comment naming the reason. The reference SHALL provide a check with a pinned ShellCheck version that runs on any checkout.

#### Scenario: Shared files checked alone
- **WHEN** the reference check runs on a reference or wrapper checkout at warning level
- **THEN** it reports no finding for `launcher/core.sh`, `launcher/windows/bootstrap.sh`, `tests/fixtures/agent/launcher.sh`, `tests/fixtures/shell-agent/launcher.sh` or `agent/launcher.sh`

#### Scenario: New finding in the core
- **WHEN** a change to `launcher/core.sh` introduces a ShellCheck warning
- **THEN** the reference check fails naming the file and line

#### Scenario: Lint-only edits keep behavior
- **WHEN** the directives and quoting are added
- **THEN** the shared launcher tests pass unchanged

### Requirement: Shared Windows shim and bootstrap
The shared launcher SHALL include the Windows shim `launcher/windows/core.ps1` and the bootstrap `launcher/windows/bootstrap.sh`, copied byte for byte from the reference tag like the other shared files. Neither SHALL contain agent identifiers: the shim SHALL read the wrapper name, file name and variable prefix from `agent/profile.json`. Setup SHALL install the bootstrap in every release.

#### Scenario: Shim edited in a wrapper
- **WHEN** a wrapper's `launcher/windows/core.ps1` differs from the reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Agent-neutral shim
- **WHEN** the alignment test scans the shim and the bootstrap
- **THEN** neither contains the reference's name, prefix or other profile identifiers

### Requirement: Thin PowerShell entry script
Each wrapper SHALL provide `<wrapper>-container.ps1` next to its Bash entry. It SHALL only set strict error handling and run the shared shim with its own directory, its arguments and whether it received pipeline input. The PowerShell entries of all wrappers SHALL be identical. Because propagation copies only shared directories, the adoption steps SHALL name the entry and the repository's `.gitattributes`.

#### Scenario: Comparing two wrappers
- **WHEN** the PowerShell entries of two wrappers are compared
- **THEN** they are byte-identical and contain no agent identifier

#### Scenario: Adopting the Windows entry
- **WHEN** a wrapper adopts the reference tag that introduces the shim
- **THEN** the propagation guide tells the operator to copy `<wrapper>-container.ps1` and `.gitattributes` from the reference

### Requirement: Scripts keep LF line endings in every repository
The reference and every wrapper SHALL carry a `.gitattributes` that checks out text files with LF line endings regardless of the user's `core.autocrlf` setting. A shared test SHALL fail when a tracked text file contains a carriage return.

#### Scenario: Clone with Git for Windows defaults
- **WHEN** a repository is cloned on Windows with `core.autocrlf=true`
- **THEN** the checked-out `.sh`, `.py` and `.ps1` files contain no carriage return

#### Scenario: Carriage return committed
- **WHEN** a tracked text file contains a carriage return
- **THEN** the shared test fails naming the file

### Requirement: PowerShell files pass PSScriptAnalyzer and logic tests
The shim and the PowerShell entry SHALL pass PSScriptAnalyzer at warning level with a pinned analyzer version, and the shim's logic tests SHALL pass on PowerShell 7. The reference SHALL provide one check that runs both, in a digest-pinned PowerShell container without network, on any reference or wrapper checkout. Windows PowerShell 5.1 SHALL be validated on a Windows host and recorded in the validation log.

#### Scenario: New analyzer finding
- **WHEN** a change to the shim introduces a PSScriptAnalyzer warning
- **THEN** the reference check fails naming the file and line

#### Scenario: Shim logic regression
- **WHEN** a change breaks argument encoding, environment selection or a refusal rule
- **THEN** the shim logic tests fail without a Windows host

#### Scenario: Windows PowerShell 5.1 validation
- **WHEN** a reference tag changes the shim, the bootstrap or the Windows entry
- **THEN** the validation log records the Windows host check of that tag on Windows PowerShell 5.1

### Requirement: Shared bootstrap tests
The bootstrap SHALL be tested by shared Linux tests that run it with a fake `wslpath` and a fake managed command. They SHALL cover argument decoding, working-directory translation and refusals, the missing installation and the entry-directory overlap.

#### Scenario: Bootstrap regression
- **WHEN** a change to the bootstrap drops empty arguments
- **THEN** the shared bootstrap tests fail on Linux without Windows
