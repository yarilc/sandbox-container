# Spec Delta

## MODIFIED Requirements

### Requirement: Setup from the Windows checkout
`<name>.ps1 --container-setup` SHALL run the interactive setup of the folder the entry runs from, a checkout or the installed copy, inside the selected distribution, which installs the release, preferences, images and managed command there. Combined with any other argument, the entry SHALL refuse it with usage guidance before running WSL. After setup, the entry SHALL state that sessions start with `<name>.ps1` from a project directory.

#### Scenario: First setup on Windows
- **WHEN** the user runs `<name>.ps1 --container-setup` in an interactive terminal
- **THEN** setup prompts in that terminal and the installation is created in the distribution, outside the Windows checkout

#### Scenario: Setup with other arguments
- **WHEN** `--container-setup` is combined with `--container-shell`
- **THEN** the entry exits with status 1 and usage guidance, and WSL runs nothing

#### Scenario: Setup from the installed copy
- **WHEN** the user runs `<name> --container-setup` through the `PATH` after an install
- **THEN** setup copies its inputs from `%LOCALAPPDATA%\Programs\<name>`

### Requirement: Windows entry help
`--container-help` SHALL take precedence over every other argument. The entry SHALL print the Windows variables `<P>_WSL_DISTRO`, `<P>_WSL_USER` and `<P>_WSL_INSTALLATION`, the supported modes and the install and uninstall options, then the checkout's wrapper help from the distribution. Help SHALL create no state and query no engine. When the distribution cannot run, it SHALL print the Windows part and the machine guidance and exit with status 0.

#### Scenario: Help with a machine
- **WHEN** the user runs `<name>.ps1 --container-help`
- **THEN** the output contains the Windows variables, `--container-install` and `--container-uninstall`, followed by the wrapper help, and the status is 0

#### Scenario: Help without a machine
- **WHEN** the distribution is not registered
- **THEN** the Windows part and the machine guidance are printed, and the status is 0

### Requirement: Checkout line endings checked before setup
Before running setup or an install, the entry SHALL refuse a checkout whose Bash entry, launcher core or agent launcher part contains a carriage return, with status 1 and a message explaining that the checkout must have LF line endings and how to renormalize it.

#### Scenario: Checkout converted to CRLF
- **WHEN** the checkout was cloned with `core.autocrlf=true` before `.gitattributes` existed
- **THEN** `--container-setup` exits with status 1 naming the first affected file and the renormalization step

#### Scenario: Install from a CRLF checkout
- **WHEN** the same checkout runs `--container-install`
- **THEN** the entry exits with status 1 naming the first affected file, before copying anything

## ADDED Requirements

### Requirement: Install and uninstall options used alone
`--container-install` and `--container-uninstall` SHALL each be refused with status 1 and usage guidance, before running WSL or changing any file, when combined with any other argument. `--container-uninstall` SHALL act on the per-user installation whether the entry runs from it or from a checkout.

#### Scenario: Install with other arguments
- **WHEN** the user runs `<name>.ps1 --container-install -c true`
- **THEN** the entry exits with status 1 naming `--container-install` alone, and nothing is copied

#### Scenario: Uninstall from a checkout
- **WHEN** the installed copy is damaged and the user runs `.\<name>.ps1 --container-uninstall` from a checkout
- **THEN** the per-user installation and its `PATH` entry are removed as from the installed command
