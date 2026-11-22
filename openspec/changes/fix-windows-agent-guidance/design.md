# Design

## Context

- `authenticate()` in `setup/setup.py` builds its pending guidance from
  `value['command']`, the managed command in the machine. `windows_entry()`
  (`WRAPPER_WINDOWS_SETUP=1`) already removes the `PATH` and managed-command
  lines from `next_steps()` and `path_guidance()`, but not from
  `authenticate()`.
- Setup knows the profile name (`NAME`, the entry is `<name>.ps1`) and each
  method's `login_args` and `credential_env`.
- `tools/windows-validate.ps1` reads the profile, and runs every case through
  a child PowerShell with `$E` bound to the entry. About twenty cases run a
  command with `-c`. The help, setup, install and refusal cases do not.
- `runner_modes()` in `tools/propagate.py` extracts labels with three
  patterns. The `==` one requires `]]` right after the label.

## Goals / Non-Goals

**Goals:**

- An agent wrapper's setup on Windows gives steps that work in PowerShell.
- The reference tools validate and plan an agent wrapper's adoption
  correctly.

**Non-Goals:**

- Other agent-specific Windows behavior; the Claude adoption validates it on
  Windows.
- Changing how setup runs the login.

## Decisions

### D1. Windows guidance in `authenticate()`

With `windows_entry()` true:

- a pending login with arguments prints
  `Next authentication action: <name>.ps1 <login args> (or reuse your selected
  existing account state).`, the arguments quoted for PowerShell with single
  quotes when needed;
- an interactive sign-in prints
  `Next authentication action: <name>.ps1 (sign in inside the interactive
  session, ...)`;
- the API method prints `Authentication pending. Set $env:<KEY> = '...' in
  PowerShell before <name>.ps1; no key is stored by setup.` The
  unrestricted-mode notice stays.

Linux output is unchanged. Alternative considered: *the entry rewrites the
output*. Setup's output reaches the console directly, as for the earlier
setup guidance.

### D2. `--container-shell` for agent profiles in `windows-validate.ps1`

The script reads `native.command` from the profile. When it is not `bash`, it
defines `$C = '--container-shell'` and every case that runs a command uses
`& $E $C -c '...'`; otherwise `$C` is empty and the cases keep `& $E -c`. The
help, setup, install, uninstall, qualification and refusal cases do not take
it. Their arguments stay the same, and the core refuses those before the
agent anyway.

### D3. Runner mode pattern

The `==` pattern accepts `== --mode` followed by optional spaces and then
`]]` or `||`. A `tests/test_propagate.py` case uses Claude's runner form and
expects both `--guard` and `--guard-idle`.

## Risks / Trade-offs

- [PowerShell quoting of login arguments.] → Login arguments are simple words
  in every profile. A value with spaces or quotes is single-quoted with
  doubled quotes, and a test covers it.
- [Validation of the Windows guidance on Windows.] → The reference profile
  has no authentication method. The unit tests cover it with the fixture
  profile, and the Claude adoption checks it on Windows.
