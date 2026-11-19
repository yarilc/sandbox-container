# Spec Delta

## ADDED Requirements

### Requirement: Proxy process budget falls back to the process rlimit
When the verified engine does not delegate the `pids` controller and the engine host counts the process rlimit per container, each session proxy SHALL be created with a soft and hard process rlimit of 128. The configured and effective limit SHALL be verified before agent execution. Otherwise the proxy process budget SHALL stay unenforced with a notice. The proxy memory budget SHALL have no fallback.

#### Scenario: Proxy on the process rlimit fallback
- **WHEN** a restricted session prepares its proxy on an engine that delegates `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** the proxy is created with a soft and hard process rlimit of 128 and without a cgroup process limit
- **AND** the effective process rlimit inside the proxy is verified before the agent starts
- **AND** the session prints a notice that the proxy process budget is enforced through the process rlimit

#### Scenario: Proxy fallback is not effective
- **WHEN** the proxy reports no process rlimit, or a value other than 128, while the fallback applies
- **THEN** preparation fails before agent execution and cleans up only owned resources
- **AND** it never substitutes an unrestricted connection

#### Scenario: Proxy fallback not applied
- **WHEN** the engine does not delegate `pids` and per-container counting is not established
- **THEN** the session requests neither a cgroup process limit nor a process rlimit for the proxy
- **AND** the session prints a notice naming the unenforced proxy process budget and why the fallback was not applied

## MODIFIED Requirements

### Requirement: Session proxies have enforced resource budgets
Each Internet-facing session proxy SHALL have a limit of 128 processes and 256 MiB memory, enforced by the engine and host cgroups, for each budget whose cgroup v2 controller (`pids`, `memory`) the verified rootless engine delegates. Startup SHALL fail before agent execution if an enforced limit is not applied, or if an unenforced limit is unexpectedly present. These budgets SHALL coexist with existing multiplex, TLS inspection and lifecycle bounds without broadening runtime access.

#### Scenario: Proxy readiness with applied limits
- **WHEN** a provider session prepares its proxy on an engine delegating the `pids` and `memory` controllers
- **THEN** both configured budgets are verified as effective before the agent starts
- **AND** matching-SNI TLS, streaming, concurrent tunnels, readiness and protected logs operate within the budgets

#### Scenario: Rootless resource control unavailable
- **WHEN** the engine rejects or silently ignores a limit whose controller it delegates, or its effective value cannot be established
- **THEN** provider preparation fails and cleans up only owned resources
- **AND** it never substitutes an unrestricted connection

#### Scenario: Controller not delegated for the proxy
- **WHEN** the verified engine does not delegate the `memory` controller
- **THEN** the proxy is created without a memory limit, and its process limit is still applied and verified when `pids` is delegated
- **AND** the session prints a notice naming the unenforced proxy budget

#### Scenario: Proxy exceeds a resource budget
- **WHEN** a proxy reaches its process or memory budget or is terminated because of exhaustion
- **THEN** affected outbound operations fail closed
- **AND** cleanup preserves the primary application/signal status and bounded shutdown contract
- **AND** other sessions retain their independent proxy resources and budgets
