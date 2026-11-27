# Spec Delta

## MODIFIED Requirements

### Requirement: Offline is the default runtime mode
An ordinary launch with an unset or empty `SANDBOX_CONTAINER_NETWORK` SHALL run in `offline` mode. `mirror` and `unrestricted` SHALL apply only when selected explicitly or supplied by validated managed preferences. `provider` and any other value SHALL fail with status 1 before engine queries, state creation or image operations, naming the accepted values `offline`, `mirror` and `unrestricted`.

#### Scenario: No mode selected
- **WHEN** the wrapper is invoked from a protected installation without `SANDBOX_CONTAINER_NETWORK`
- **THEN** the session starts in offline mode and stderr reports `network mode=offline`

#### Scenario: Explicit unrestricted mode
- **WHEN** `SANDBOX_CONTAINER_NETWORK=unrestricted` is set
- **THEN** the session starts with ordinary runtime networking and no guard or proxy

#### Scenario: Provider mode requested
- **WHEN** `SANDBOX_CONTAINER_NETWORK=provider` is set
- **THEN** the wrapper exits with status 1, states that the reference profile declares no authentication method, and performs no engine or image operation

#### Scenario: Explicit mirror mode
- **WHEN** `SANDBOX_CONTAINER_NETWORK=mirror` is selected for a qualified installation
- **THEN** the session reports `network mode=mirror` and reaches approved dependency profiles through the confined mirror
- **AND** the launch uses the restricted guard and no provider policy or authentication method
