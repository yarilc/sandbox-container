## ADDED Requirements

### Requirement: Engine image declares its capabilities
The engine image SHALL declare in its `io.containers.capabilities` label exactly the capabilities that the engine container is started with: `SETUID`, `SETGID`, `SYS_CHROOT` and `CHOWN`. Starting an engine SHALL therefore report no capability error. The label SHALL NOT add a capability to the engine: its capabilities stay the fixed hardening exceptions.

#### Scenario: Engine started by a session
- **WHEN** a session starts its engine through a Podman engine that reads the image's capability label
- **THEN** Podman reports no `Capabilities requested by user or image are not allowed by default` error, and the engine's bounding set is `SETUID`, `SETGID`, `SYS_CHROOT` and `CHOWN`

#### Scenario: Label and options drift apart
- **WHEN** the engine recipe's capability label differs from the capabilities of the engine container options
- **THEN** the shared engine recipe check fails, naming the difference
