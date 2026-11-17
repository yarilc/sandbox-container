# Spec Delta

## Purpose

Defines how every wrapper's launcher is built from one shared Bash core and a small agent part, so launcher behavior is specified, fixed and tested once for all wrappers.

## ADDED Requirements

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
