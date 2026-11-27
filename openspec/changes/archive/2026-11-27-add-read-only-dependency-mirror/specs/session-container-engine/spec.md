# Spec Delta

## MODIFIED Requirements

### Requirement: Engine shares the session network boundary
The engine and every container it runs SHALL have no network path other than the session's:
- an offline session's engine SHALL reach no external service;
- a mirror session's engine SHALL reach only the dependency mirror within the session's network boundary;
- a provider session's engine SHALL reach the dependency mirror and the approved CONNECT destinations through their respective trusted frontends;
- an unrestricted session's engine SHALL have the session's network.

#### Scenario: Offline nested container
- **WHEN** a container started by an offline session's engine tries direct DNS, TCP or UDP to an external address, or the engine tries to pull an image
- **THEN** every attempt fails, and no network path appears that the session lacks

#### Scenario: Interfaces of a restricted session with an engine
- **WHEN** a restricted session with an engine lists the interfaces of its network namespace (`/proc/net/dev`)
- **THEN** only loopback is present, although the host's `/sys`, which Podman bind-mounts read-only into a container that joins another network namespace, lists the host's interfaces

#### Scenario: Unrestricted pull
- **WHEN** an unrestricted session's engine pulls an image that is not in the library
- **THEN** the pull uses the session's network and the image stays in the session's storage

#### Scenario: Dependency download from a nested container or build
- **WHEN** a nested container or a build `RUN` joins the engine's network namespace with `--network=host` in a restricted session with an active mirror profile
- **THEN** the child can fetch an approved dependency from the session's loopback mirror
- **AND** access uses the same approved routes as the session and gives the child no host networking, external DNS or direct upstream connection

#### Scenario: Networking disabled for a nested operation
- **WHEN** a nested container or build step runs with `--network=none`
- **THEN** it cannot reach the session's mirror endpoint
