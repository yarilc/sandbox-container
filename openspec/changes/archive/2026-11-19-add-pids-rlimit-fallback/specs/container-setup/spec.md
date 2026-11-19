# Spec Delta

## MODIFIED Requirements

### Requirement: Saved budgets govern managed launches and verification
The managed launcher SHALL supply the saved budgets and lifetime through `SANDBOX_CONTAINER_MEMORY_LIMIT`, `SANDBOX_CONTAINER_CPU_LIMIT`, `SANDBOX_CONTAINER_PIDS_LIMIT` and `SANDBOX_CONTAINER_RUN_TIMEOUT` when these are absent from the launch environment. An explicitly present variable SHALL take precedence. Setup smoke and qualification SHALL use the saved values for every budget the engine can enforce, through its cgroup controller or the process rlimit fallback.

#### Scenario: Managed launch uses saved budgets
- **WHEN** the user launches through the managed command with no budget variables exported
- **THEN** the shell container receives the saved budgets and lifetime
- **AND** a restricted launch matches the qualification report produced by setup

#### Scenario: Explicit override differs from qualified values
- **WHEN** the user exports `SANDBOX_CONTAINER_MEMORY_LIMIT=16g` for a restricted managed launch qualified with `4g`
- **THEN** the override is used and the qualification check stops the launch with requalification guidance

#### Scenario: Smoke verifies saved values
- **WHEN** setup runs its installed smoke check
- **THEN** the smoke compares the effective cgroup limits of every cgroup-enforced budget with the saved budgets, not with ambient environment values
- **AND** when the process budget uses the rlimit fallback, it compares the effective soft and hard process rlimit with the saved process budget
- **AND** it requires every budget whose controller is missing to have no cgroup limit

#### Scenario: Setup plan names unenforced budgets
- **WHEN** setup runs on an engine that does not delegate the `cpu` controller
- **THEN** the setup plan lists the CPU budget as not enforced, with the missing controller, and setup continues without an extra question

#### Scenario: Setup plan names the process rlimit fallback
- **WHEN** setup runs on an engine that does not delegate the `pids` controller, on a host that counts the process rlimit per container
- **THEN** the setup plan lists the process budget as enforced through the process rlimit, with the missing controller, and setup continues without an extra question

#### Scenario: Setup plan names a cgroup manager without limits
- **WHEN** setup runs on a rootless engine with the `cgroupfs` cgroup manager that reports every controller
- **THEN** the setup plan lists no enforced cgroup budget, names the `cgroupfs` manager as the reason for the memory and CPU budgets, and lists the process budget mechanism
- **AND** setup continues without an extra question
