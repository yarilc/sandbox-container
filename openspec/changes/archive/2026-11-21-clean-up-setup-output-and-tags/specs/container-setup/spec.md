# Spec Delta

## MODIFIED Requirements

### Requirement: Repeatable setup with owned recovery
Rerunning setup SHALL review saved choices and reuse valid artifacts. Activation SHALL preserve the previous working installation until the candidate passes validation. Cancellation, interruption or failure SHALL remove only setup-owned temporary resources, preserve credentials and unrelated containers, and report persistent changes already made. Concurrent setup runs SHALL NOT overwrite each other's activation.

#### Scenario: Rerun or interrupted update
- **WHEN** setup is rerun unchanged or interrupted while preparing an update
- **THEN** unchanged suitable artifacts need no rebuild and the last activated launcher remains usable
- **AND** any created images or enabled user socket remaining after interruption are reported without deleting shared resources

#### Scenario: Abandoned candidate tags
- **WHEN** setup fails, is cancelled or is interrupted after it tagged images `setup-<release>` for its candidate release
- **THEN** it removes those tags before exiting, keeps every other tag of the same images and the tags of retained releases and other installation roots, and reports an image left without a name with the command that removes it

#### Scenario: Competing activation
- **WHEN** another setup already holds the target installation's update lock
- **THEN** setup exits with an actionable busy message without modifying that installation

#### Scenario: Unrelated launcher exists
- **WHEN** the desired command path contains a file not owned by this setup
- **THEN** setup offers a different path or stops without overwriting that file

#### Scenario: Managed command path changes
- **WHEN** a validated candidate chooses a different physical command entry
- **THEN** activation retires the previous owned command only after publishing the new command
- **AND** retirement or publication failure restores the previous activation and command
- **AND** two path spellings of the same physical entry do not cause its removal

#### Scenario: Group leader exits before timeout cleanup
- **WHEN** a setup-owned process group has surviving descendants after its leader exits or its captured pipes close
- **THEN** timeout or interruption cleanup terminates the remaining owned group within bounded teardown time
- **AND** the primary timeout/interruption remains the reported outcome

## ADDED Requirements

### Requirement: Setup started by the Windows entry
When the Windows entry starts setup, setup SHALL omit the shell `PATH` guidance and the managed-command lines for launching and reviewing setup from its plan and summary, and SHALL state that the Windows entry starts sessions. Setup started from a Linux shell SHALL keep that guidance.

#### Scenario: Setup from the Windows entry
- **WHEN** the user runs `<name>.ps1 --container-setup`, or `--container-install` runs setup from the installed copy
- **THEN** the setup output contains no `export PATH=` line, no shell startup file and no distribution path of the managed command, and the entry then prints how to start sessions

#### Scenario: Setup from a Linux shell
- **WHEN** setup runs from a Linux shell whose `PATH` lacks the managed command directory
- **THEN** it prints the `export PATH=` guidance and the managed-command lines as before
