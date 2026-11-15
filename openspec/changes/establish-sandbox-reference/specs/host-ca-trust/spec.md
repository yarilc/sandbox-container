# Spec Delta

## MODIFIED Requirements

### Requirement: Host CA trust is disabled by default
The wrapper SHALL NOT mount any host certificate bundle and SHALL NOT set CA bundle environment variables unless host CA trust is enabled.

#### Scenario: Variable not set
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_TRUST_HOST_CA` unset
- **THEN** the container has no host certificate mount and no `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `CURL_CA_BUNDLE` or `NODE_EXTRA_CA_CERTS` variables set by the wrapper

#### Scenario: Variable disabled explicitly
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_TRUST_HOST_CA` set to `0`, `false` or `no`
- **THEN** the behavior is the same as when the variable is unset

### Requirement: Host CA trust is enabled by an explicit flag
The wrapper SHALL enable host CA trust when `SANDBOX_CONTAINER_TRUST_HOST_CA` is set to `1`, `true` or `yes`, case-insensitively. Any other non-empty value SHALL cause the wrapper to fail before starting the container, with an error message that names the variable and the accepted values.

#### Scenario: Variable enabled
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_TRUST_HOST_CA` set to `1`
- **THEN** host CA trust is enabled

#### Scenario: Invalid value
- **WHEN** the wrapper starts with `SANDBOX_CONTAINER_TRUST_HOST_CA` set to `maybe`
- **THEN** the wrapper exits with a non-zero status and prints an error naming `SANDBOX_CONTAINER_TRUST_HOST_CA` and the accepted values, and no container is started

### Requirement: Bundle selection
When host CA trust is enabled, the wrapper SHALL use the file named by `SANDBOX_CONTAINER_CA_BUNDLE` if that variable is set. If it is not set, the wrapper SHALL use the first existing file among `/etc/ssl/certs/ca-certificates.crt` and `/etc/pki/tls/certs/ca-bundle.crt`.

#### Scenario: Explicit bundle path
- **WHEN** host CA trust is enabled and `SANDBOX_CONTAINER_CA_BUNDLE` names an existing file
- **THEN** that file is the bundle exposed to the container

#### Scenario: Default bundle path
- **WHEN** host CA trust is enabled, `SANDBOX_CONTAINER_CA_BUNDLE` is unset, and `/etc/ssl/certs/ca-certificates.crt` exists
- **THEN** that file is the bundle exposed to the container

#### Scenario: No bundle found
- **WHEN** host CA trust is enabled, `SANDBOX_CONTAINER_CA_BUNDLE` is unset, and neither default path exists
- **THEN** the wrapper exits with a non-zero status and prints an error asking the user to set `SANDBOX_CONTAINER_CA_BUNDLE`

#### Scenario: Explicit bundle path missing
- **WHEN** host CA trust is enabled and `SANDBOX_CONTAINER_CA_BUNDLE` names a file that does not exist
- **THEN** the wrapper exits with a non-zero status and prints an error naming the variable and the path, and no container is started
