# Spec Delta

## MODIFIED Requirements

### Requirement: Ephemeral constrained temporary storage
Sessions SHALL explicitly provide ephemeral `/tmp`, `/run`, `/var/tmp` and, in shared-state mode, home mounts with `rw,nosuid,nodev,noexec`. Limits SHALL be 512 MiB for `/tmp`, 32 MiB for `/run`, 512 MiB for `/var/tmp` and 512 MiB for the ephemeral home. `/tmp`, `/var/tmp` and the ephemeral home SHALL permit caller writes with sticky directory mode `1777`. A profile that declares executable temporary storage (`native.exec_tmp`) SHALL drop `noexec` from `/tmp` and the ephemeral home only; `/var/tmp` and `/run` SHALL always be `noexec`. The reference profile declares none. Temporary contents SHALL disappear after container removal. Internal sandbox compatibility SHALL NOT silently relax these options.

#### Scenario: Temporary file lifecycle
- **WHEN** a session writes temporary files in `/tmp` and `/var/tmp` and a new container starts after its removal
- **THEN** both paths accept caller writes but the previous files are absent
- **AND** all three temporary mounts retain `nosuid,nodev,noexec` and their specified limits

#### Scenario: Temporary mounts are explicit
- **WHEN** a shell session is created in shared or isolated state mode
- **THEN** `/tmp`, `/run`, `/var/tmp` and `/dev/shm` are explicitly provisioned, and `/dev` with its `devpts` is left to the engine
- **AND** no writable `/var/log` tmpfs or writable `/dev/shm` is introduced by automatic read-only provisioning

#### Scenario: Execution restrictions apply to both temporary directories
- **WHEN** a session attempts to execute a copied executable directly from `/tmp` or `/var/tmp`
- **THEN** the mount policy prevents direct execution from either directory
- **AND** ordinary temporary file writes remain possible

#### Scenario: Profile declares executable temporary storage
- **WHEN** a profile sets `native.exec_tmp` to true
- **THEN** `/tmp` and the ephemeral home allow execution while `/var/tmp` and `/run` keep `noexec`
