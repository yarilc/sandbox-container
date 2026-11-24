## MODIFIED Requirements

### Requirement: Process budget falls back to the process rlimit
When the verified engine does not delegate the `pids` controller and the engine host counts the process rlimit per container, the shell container's first process SHALL set its soft and hard process rlimit to the selected process budget before the container's program runs. The engine SHALL apply no process rlimit for the budget: one applied at creation counts every container of the user. Otherwise the process budget SHALL stay unenforced. Memory and CPU SHALL have no fallback.

#### Scenario: Process controller missing on a per-container host
- **WHEN** a session starts with the default budgets on an engine delegating `cpu` and `memory` but not `pids`, on a host that counts the process rlimit per container
- **THEN** the container's first process sets a soft and hard process rlimit of 512 before the application, or the guard in restricted modes, runs
- **AND** the container is created without a cgroup process limit and without a process rlimit requested from the engine
- **AND** the memory and CPU limits are applied as before

#### Scenario: Process controller delegated
- **WHEN** the engine delegates the `pids` controller
- **THEN** the process budget is enforced only by the cgroup process limit
- **AND** the wrapper sets no process rlimit

#### Scenario: Per-container counting not established
- **WHEN** the engine does not delegate `pids` and the host is not known to count the process rlimit per container
- **THEN** the wrapper requests neither a cgroup process limit nor a process rlimit for the container
- **AND** the session continues with a notice that names the unenforced process budget and why the fallback was not applied

#### Scenario: Memory controller missing
- **WHEN** the engine does not delegate the `memory` controller
- **THEN** the memory budget stays unenforced and no substitute memory limit is set

#### Scenario: The session cannot raise its process rlimit
- **WHEN** a process in a session on the fallback tries to raise its soft or hard process rlimit above the selected budget
- **THEN** the attempt fails, because the session has no capabilities and no-new-privileges is set

#### Scenario: Concurrent sessions have independent limits
- **WHEN** two sessions on the fallback run at the same time and the first holds processes up to its limit
- **THEN** the second session can still create processes up to its own limit

#### Scenario: Other containers do not consume the session's budget
- **WHEN** other containers of the same user, such as proxies, engines or their nested containers, together hold more processes than the session's budget
- **THEN** the session starts, and can create processes up to its own budget

#### Scenario: The limit cannot be set
- **WHEN** the container's first process cannot set the process rlimit to the selected budget
- **THEN** the container stops before the application or the guard runs, and the launch exits non-zero

### Requirement: Process rlimit fallback is verified
When the process budget uses the rlimit fallback, each launch SHALL require the created agent container to start with the step that sets the selected budget, and to carry no process rlimit requested by the wrapper. Setup smoke and restricted qualification SHALL measure the effective limit inside the agent container. A mismatch SHALL stop startup or setup with an actionable diagnostic, without a retry using weaker limits.

#### Scenario: Engine drops the process rlimit
- **WHEN** the created container does not start with the step that sets the selected budget, for example because the engine dropped or replaced its entry command, or the step sets another value, or the container carries a process rlimit requested by the wrapper
- **THEN** the wrapper removes only its own container and exits non-zero before the application starts
- **AND** the diagnostic names the process rlimit fallback

#### Scenario: Effective rlimit is measured
- **WHEN** setup smoke or the restricted qualification probe runs inside an agent container on the fallback
- **THEN** it reads the effective soft and hard process rlimit and requires both to equal the selected budget
- **AND** it requires the cgroup process interface to be absent or unlimited
