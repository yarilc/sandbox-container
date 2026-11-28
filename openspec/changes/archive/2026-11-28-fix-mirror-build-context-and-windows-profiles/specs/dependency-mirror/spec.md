# Spec Delta

## MODIFIED Requirements

### Requirement: Operator-managed mirror library
The host SHALL provide `--container-mirror add <catalog-name|file>`, `list`, `remove <name>` and `verify [<name>]` through each wrapper. The private shared library SHALL store only validated, versioned profiles on protected native storage. The protected release SHALL supply the public catalog. Profiles SHALL identify named upstreams by ecosystem and approved HTTPS base URL.

#### Scenario: Catalog profile
- **WHEN** the operator adds a name available in the protected catalog
- **THEN** the profile becomes installed and `list` displays its name, revision and default status
- **AND** `list` identifies other available catalog entries

#### Scenario: Operator profile file
- **WHEN** the operator adds a well-formed profile file outside the writable mounts of the workspace and state, including a widened worktree scope
- **THEN** the command publishes a complete validated profile atomically
- **AND** relative file and Windows drive paths follow the host command's existing context rules

#### Scenario: Windows drive operator profile file
- **WHEN** the operator invokes `--container-mirror add` through the Windows entry with an explicit Windows drive path or a relative path resolving onto a mounted Windows drive outside the writable workspace, widened worktree, state, and entry mounts
- **THEN** the command accepts the regular non-symlink file without requiring POSIX mode bits on the Windows drive mount and publishes the validated profile atomically into the protected native library
- **AND** it still rejects symlink aliases, files overlapping writable mounts, unsafe native Linux paths, and any mirror library path outside protected native storage

#### Scenario: Repository declares a separate package origin
- **WHEN** an operator profile declares an additional HTTPS artifact prefix for a repository
- **THEN** the profile records the prefix and its own address policy
- **AND** the mirror authorizes package reads only on that prefix's supported artifact routes

#### Scenario: Invalid or writable profile source
- **WHEN** a profile is malformed, mentions an unsupported ecosystem, contains credentials, or resolves into a writable mount
- **THEN** the command reports the cause without any fetch or partial library update

#### Scenario: Removal and verification
- **WHEN** the operator verifies an installed profile
- **THEN** the command probes the index of each upstream using the mirror's outbound policy, reports each result and signals failure if any probe fails
- **AND** removing the profile excludes it from subsequent launches
