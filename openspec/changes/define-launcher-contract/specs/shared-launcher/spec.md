# Spec Delta

## Purpose

Defines how every wrapper's launcher is built from one shared Bash core and a small agent-specific part, so launcher behavior is specified, fixed and tested once for all wrappers.

## ADDED Requirements

### Requirement: One shared launcher core
Every wrapper SHALL run its sessions through the same shared Bash launcher core, copied byte for byte from the reference tag and recorded in the reference-copy manifest like the other shared files. The core SHALL contain no agent identifiers and SHALL need no host tool beyond those the launchers already require; in particular it SHALL NOT require host Python.

#### Scenario: Core edited in a wrapper
- **WHEN** a wrapper's copy of the launcher core differs from the reference tag
- **THEN** the reference-copy test fails naming the file

#### Scenario: Host without Python
- **WHEN** an unrestricted session starts on a host without Python
- **THEN** the shared core launches it as today, and only optional diagnostics are skipped

### Requirement: Thin wrapper entry script
Each wrapper's `<wrapper>-container.sh` SHALL only locate its installation and hand control to the shared core with the wrapper's agent part. It SHALL hold no launcher logic of its own.

#### Scenario: Comparing two wrappers
- **WHEN** the entry scripts of two wrappers are compared after replacing the wrapper name
- **THEN** they are identical

### Requirement: Agent launcher part consistent with the profile
Each wrapper SHALL provide one agent launcher file with the profile values the core needs (for example the variable prefix, wrapper name, images, native home and agent command) and the agent hooks. The values SHALL equal those in `agent/profile.json`, checked by a credential-free test.

#### Scenario: Profile and launcher part disagree
- **WHEN** the agent launcher file and `agent/profile.json` declare different values for the same property
- **THEN** the alignment test fails naming the property

### Requirement: Common launcher interface
Every wrapper SHALL accept the same `--container-*` options and the same `<PREFIX>_*` configuration variables, with the same meaning and defaults, as defined by the shared core. An agent-specific option or variable SHALL be declared through the agent hooks and SHALL appear in `--container-help` with the common ones.

#### Scenario: Common option in any wrapper
- **WHEN** a common option or variable is used with any wrapper
- **THEN** it behaves as the shared core defines it

#### Scenario: Agent-specific variable
- **WHEN** a wrapper declares an extra variable through its hooks
- **THEN** `--container-help` lists it, and the other wrappers neither accept nor document it

### Requirement: Bounded agent hooks
The shared core SHALL call agent code only at documented hook points with a documented input and output. A missing optional hook SHALL fall back to the core's default behavior. No hook SHALL replace the session lifecycle: name reservation, budget verification, start, lifetime notice, signal handling, shutdown and recovery.

#### Scenario: Wrapper without optional hooks
- **WHEN** an agent launcher file defines none of the optional hooks
- **THEN** the session runs with the core's default behavior

#### Scenario: Hook output outside its contract
- **WHEN** a hook returns a value the contract does not allow, such as a mount over a protected path
- **THEN** the core refuses to start the session and names the hook

### Requirement: Shared launcher tests
The launcher core SHALL be tested by a shared test suite. The suite SHALL run against a fixture agent launcher file and a shared fake engine, and SHALL be copied unchanged into every wrapper. A wrapper's own launcher tests SHALL cover only its hooks and its real-image runtime behavior.

#### Scenario: Lifecycle defect fixed once
- **WHEN** a lifecycle defect is fixed in the reference core together with a shared test
- **THEN** every wrapper that adopts the tag receives both the fix and the test without editing its own files

### Requirement: Recorded launcher differences
`docs/launcher-contract.md` in the reference SHALL list each launcher difference found between the wrappers, the behavior chosen for the core, and where an agent-specific difference lives. A difference left to a hook SHALL name the hook.

#### Scenario: Reviewing a wrapper difference
- **WHEN** a maintainer finds behavior that differs between two wrappers
- **THEN** the document either records it with its hook or shows it as a defect to fix in the core
