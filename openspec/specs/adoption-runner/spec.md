# adoption-runner Specification

## Purpose

Run a wrapper adoption's follow-up verification on WSL or a native Linux host in one step, after the adoption closes in its working session: the commands the propagation tool selects for the tag, with full logs, a summary and one archive for the maintainer.

## Requirements

### Requirement: Runner runs the checklist of an adopted wrapper
`tools/adoption-run.sh` SHALL take a wrapper checkout, the old tag and the new tag. It SHALL run, from the checkout's root and in order, exactly the commands that `tools/propagate.py --checklist` prints for that checkout. A checkout whose manifest does not name the new tag and its commit SHALL be refused before anything runs.

#### Scenario: Adopted checkout
- **WHEN** the operator runs the runner on a wrapper checkout whose manifest names `sandbox-ref-36` and its commit, from `sandbox-ref-35`
- **THEN** it runs each command of the checklist for that range, and only those

#### Scenario: Checkout on another tag
- **WHEN** the wrapper checkout's manifest still names the old tag
- **THEN** the runner exits nonzero naming both tags, and runs no command

### Requirement: Preflight before the suites
Before any suite, the runner SHALL record:
- the checkout's commit;
- the kernel, the Podman version, the cgroup manager and controllers, and the OCI runtime;
- the free space of the home and temporary directories.

It SHALL check the images the selected commands need:
- the runtime image always;
- the guard toolchain for `--guard`, `--network` or `--qualification`.

When an image is missing or less than 1 GiB is free, it SHALL run no command and still write the summary and the archive.

#### Scenario: Missing guard toolchain
- **WHEN** the checklist selects `--network` and the wrapper's guard toolchain image is absent
- **THEN** the summary names the missing image, no command runs, and the runner exits nonzero

#### Scenario: Low disk space
- **WHEN** the home directory has less than 1 GiB free
- **THEN** the summary names the free space, no command runs, and the runner exits nonzero

### Requirement: Engine image prepared from the checkout
When the tag changes an input of the engine image, the runner SHALL rebuild the wrapper's engine image from the checkout's `launcher/engine/` before any runtime command, without pulling. It SHALL record the image ID and the `io.containers.capabilities` label. When no input changed, it SHALL leave the engine image as it is.

#### Scenario: Engine inputs changed
- **WHEN** the range adds `launcher/engine/start.sh`
- **THEN** the runner rebuilds `<agent image>-engine:latest` before the runtime commands, and the summary records its ID and label

#### Scenario: Engine inputs unchanged
- **WHEN** the range changes only guard code
- **THEN** the runner builds no engine image

### Requirement: Host unit tests with private storage
The runner SHALL run the checklist's host unit tests with `SANDBOX_TEST_TMPDIR` on a new private directory:
- on the host's Python, when it is 3.11 or later;
- otherwise in the wrapper's runtime image, without network and with a private tmpfs.

The summary SHALL say where they ran.

#### Scenario: Host with Python 3.12
- **WHEN** the runner runs on WSL with Python 3.12
- **THEN** the host unit tests run on the host, with `SANDBOX_TEST_TMPDIR` on a directory of mode 0700 that the runner created

#### Scenario: Host with Python 3.9
- **WHEN** the runner runs on the Rocky 9 lab host with Python 3.9
- **THEN** the host unit tests run in the runtime image, and the summary says so

### Requirement: Full logs and a summary
Each command SHALL write its full output to its own log. A failed command SHALL NOT stop the later ones. The summary SHALL list each command with its exit status and its last `OK` or `FAILED` line, then every skipped test with its reason. The runner SHALL exit zero only when every command passed and no test skipped because an image was not prepared.

#### Scenario: Failure in the middle
- **WHEN** the second of five commands fails
- **THEN** the other four still run, and the summary shows the failure with its exit status

#### Scenario: Skip for an image not prepared
- **WHEN** a test skips with a reason that asks to prepare an image in the engine first
- **THEN** the summary lists that skip as not prepared, and the runner exits nonzero

### Requirement: One archive per run
Each run SHALL write a new log directory and one archive in the home directory. Both names SHALL name the wrapper, the new tag, the start time and the host. The run SHALL record the image list before and after the commands. Around `--setup-runtime` it SHALL also record the image tags and their difference.

#### Scenario: Two runs on the same day
- **WHEN** the operator runs the runner twice for the same wrapper and tag
- **THEN** the second run writes a new directory and a new archive, and the first archive is unchanged

#### Scenario: Setup runtime leaves the tags
- **WHEN** `--setup-runtime` runs
- **THEN** the archive holds the image tags before and after it and their difference, and the summary states whether they are equal

### Requirement: Rerun of chosen entries
With `--only` and a comma-separated list of checklist entry names, the runner SHALL run the preflight and only those entries, into a new log directory and archive. An unknown entry name SHALL be refused before anything runs.

#### Scenario: Rerun of the unit tests
- **WHEN** the operator runs the runner with `--only unit` after fixing a failure
- **THEN** only the host unit tests run, in a new directory and archive

#### Scenario: Unknown entry
- **WHEN** `--only` names an entry the checklist does not print
- **THEN** the runner exits nonzero naming the entry and the valid names, and runs nothing

### Requirement: No side effects outside the logs
The runner SHALL NOT commit, switch branches, fetch, push, remove images or containers, or change the checkout. Besides the logs, the archive and the private temporary directory, it SHALL only rebuild the engine image tag.

#### Scenario: Checkout after a run
- **WHEN** a run finishes
- **THEN** `git status --porcelain` in the checkout is unchanged, and no image tag other than the engine image's was added or removed by the runner itself
