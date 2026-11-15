# Spec Delta

## MODIFIED Requirements

### Requirement: Document parent-directory usage and access scope
Wrapper help SHALL list `--container-git-worktree` and explain the parent mount. The README SHALL show usage from a worktree root, shell-mode composition, the mounted and initial paths, direct parent selection, writable sibling access, and the limitation for Git references outside that parent.

#### Scenario: Read documented worktree usage
- **WHEN** a user reads the README instructions for `--container-git-worktree`
- **THEN** an example changes directory to `/path/to/root/main` and invokes the wrapper using an absolute script path or the documented alias
- **AND** the text explains that `/path/to/root` is mounted read/write while the shell starts in `/path/to/root/main`
- **AND** it explains that sibling contents become writable, no Git root detection occurs, and references outside the parent are not exposed by this option
- **AND** an example combines the option with `--container-shell`

#### Scenario: Discover the option in wrapper help
- **WHEN** the caller runs `--container-help`
- **THEN** help lists `--container-git-worktree` and describes mounting the parent of the current directory

### Requirement: Explicit unsafe workspace override
`SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` SHALL be the only value that permits a refused workspace. When it is used, the wrapper SHALL print a stderr warning naming the exposed path before continuing. Any other value SHALL leave the refusal in force. The override SHALL NOT relax any other mount, state or network check.

#### Scenario: Exact override
- **WHEN** the caller sets `SANDBOX_CONTAINER_ALLOW_UNSAFE_WORKSPACE=1` and launches from a refused directory
- **THEN** the wrapper warns that the sensitive directory is explicitly exposed and continues startup

#### Scenario: Non-exact override
- **WHEN** the variable is set to `true`, `yes` or any value other than `1`
- **THEN** the refusal remains in force

## ADDED Requirements

### Requirement: Worktree option composition
The wrapper SHALL consume `--container-git-worktree` as a boolean option without forwarding it to Bash. It SHALL support this option with `--container-shell` and `--container-build` and preserve other Bash arguments under the existing forwarding rules.

#### Scenario: Bash arguments are forwarded
- **WHEN** the caller launches with `--container-git-worktree -c "git status"`
- **THEN** Bash receives `-c` and `git status` as separate arguments
- **AND** Bash does not receive `--container-git-worktree`

#### Scenario: Shell mode uses the parent mount
- **WHEN** the caller launches from `/path/to/root/main` with `--container-shell --container-git-worktree`
- **THEN** the shell starts in `/path/to/root/main` with `/path/to/root` mounted read/write at its host path

#### Scenario: Explicit image build and parent mount
- **WHEN** the caller launches with `--container-build --container-git-worktree`
- **THEN** the wrapper builds the image before starting the container with the parent-directory workspace mount

### Requirement: Launch directory is the working directory
The wrapper SHALL use the physical current directory as the container working directory and the basis for container naming, whether or not `--container-git-worktree` is present.

#### Scenario: The shell starts in the selected worktree
- **WHEN** the caller launches from `/path/to/root/main` with `--container-git-worktree`
- **THEN** the container working directory is `/path/to/root/main`
- **AND** the container name uses `main` as its prefix under the existing naming rules

## REMOVED Requirements

### Requirement: Launch directory is preserved
**Reason**: Its scenarios named the Claude wrapper; the behavior is restated for the reference shell.
**Migration**: See "Launch directory is the working directory".

### Requirement: Wrapper option composition
**Reason**: Its scenarios named the Claude wrapper; the behavior is restated for the reference shell.
**Migration**: See "Worktree option composition".
