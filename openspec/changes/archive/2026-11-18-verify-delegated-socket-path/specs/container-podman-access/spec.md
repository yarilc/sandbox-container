## MODIFIED Requirements

### Requirement: Exposed Podman service must report rootless operation
With API access enabled, the wrapper SHALL explicitly query the selected Unix endpoint and require successful rootless `true` and an absolute service-reported host socket path. The host socket path, after removing a `unix://` prefix, SHALL NOT consist only of slash characters. When that path exists in the wrapper's own filesystem namespace, it SHALL be a Unix socket. Query failure or an invalid result SHALL fail before image operations or launch with an actionable error identifying the endpoint. The host-side path SHALL be the bind source exposed at `/run/podman/podman.sock`. Guided setup SHALL apply the same checks when it verifies the endpoint.

#### Scenario: Rootless service is verified
- **GIVEN** the selected Unix socket exists and its service reports rootless `true` and an absolute host socket path
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_PODMAN=1`
- **THEN** verification succeeds before image operations and container startup
- **AND** the service-reported socket mount and container `CONTAINER_HOST` are supplied

#### Scenario: Rootful service is rejected
- **GIVEN** the selected Unix socket exists and its service reports rootless operation as `false`
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_PODMAN=1`
- **THEN** it exits nonzero before image operations or container startup
- **AND** the error identifies the socket and explains that a rootless service is required

#### Scenario: Unreachable service is rejected
- **GIVEN** the selected Unix socket exists but the service query fails
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_PODMAN=1`
- **THEN** it exits nonzero before image operations or container startup
- **AND** the error identifies the socket and directs the user to check the service and access permissions

#### Scenario: Unrecognized service result is rejected
- **GIVEN** the service query succeeds but returns an empty or unexpected rootless result
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_PODMAN=1`
- **THEN** it exits nonzero before image operations or container startup because rootless operation was not confirmed
- **AND** the error identifies the socket and explains the rootless requirement

#### Scenario: Verification targets the exposed endpoint
- **GIVEN** default Podman configuration points at a different service from the selected delegation endpoint
- **WHEN** the wrapper verifies enabled API access
- **THEN** verification explicitly queries the selected Unix endpoint and uses that service's result

#### Scenario: Verification applies in all enabled launch modes
- **WHEN** enabled access is used with or without `--container-shell`, including with `--container-build` and `--container-git-worktree`
- **THEN** the same service verification gates image operations and container startup
- **AND** a failed verification prevents even an explicitly requested image build

#### Scenario: Socket is remapped in the wrapper container
- **GIVEN** the wrapper reaches a same-host service through a remapped Unix path
- **WHEN** the selected endpoint reports a different absolute host-side socket path that does not exist in the wrapper's namespace
- **THEN** the outer launch binds that host-side path rather than the client-visible path
- **AND** the documentation states that the service's answer is trusted in this case

#### Scenario: Host socket path is invalid
- **WHEN** an enabled delegation endpoint reports rootless `true` but a missing or relative host socket path
- **THEN** startup fails before image operations with a socket-specific diagnostic

#### Scenario: Host socket path is the root directory
- **WHEN** an enabled delegation endpoint reports `/`, `//` or `unix:///` as its host socket path
- **THEN** startup fails before image operations with a socket-specific diagnostic, and the host root is never mounted

#### Scenario: Host socket path is not a socket
- **WHEN** an enabled delegation endpoint reports a host socket path that exists in the wrapper's namespace as a directory, a regular file or another non-socket
- **THEN** startup fails before image operations naming the reported path, and nothing is mounted from it

#### Scenario: Setup verifies the same rule
- **WHEN** guided setup verifies an endpoint whose service reports a slash-only path or an existing non-socket path
- **THEN** setup reports that the endpoint did not report a usable host socket and does not save it
