# Design

## Context

- `launcher/core.sh` builds `setup_command` as `bash <invoked wrapper>
  --container-setup` (line 320) and uses it in two refusals:
  - a restricted mode without a protected installation (line 326);
  - a default provider launch without saved settings (line 334).
- From Windows, the bootstrap exports `WRAPPER_WINDOWS_ENTRY`, the translated
  directory of the Windows entry. `setup/launch.py` keeps the environment
  (`runtime_environment` copies `os.environ`), so the wrapper sees it. The
  shim never forwards a user variable with the `WRAPPER_WINDOWS_` prefix.
- `AGENT_NAME` equals the profile name in every wrapper, and the Windows entry
  is `<profile name>.ps1`.
- `tools/windows-validate.ps1` already has `-Install` and `-StopMachine`. Its
  mode cases follow the saved mode: the unprepared-restricted case runs only
  after an unrestricted setup.

## Goals / Non-Goals

**Goals:**

- A Windows user who asks for a restricted mode that setup did not prepare
  reads the Windows step.
- The installer, the stopped-machine refusals and the unprepared restricted
  mode pass on Windows with the code that sessions and setup now use.

**Non-Goals:**

- `-Install` on an agent wrapper (after propagation).
- Testing a `sudo` that asks for a password on the real machine: it would
  change the machine's sudoers; `tests/test_windows_enter.py` covers it.

## Decisions

### D1. The Windows step in the launcher's guidance

When `WRAPPER_WINDOWS_ENTRY` is not empty, the core sets the next step to
`run <AGENT_NAME>.ps1 --container-setup from Windows`; otherwise it stays
`run bash <wrapper> --container-setup and use the managed launcher`. Both
refusals use that step:

- `setup required: offline sessions need a protected installation; run
  <name>.ps1 --container-setup from Windows, or set <P>_NETWORK=unrestricted
  for a direct session`;
- the provider refusal, with the same step.

The installed command also accepts `<name>.ps1`, because PowerShell resolves
the bare name to that file on `PATH`.

Alternative considered: *the shim rewrites the message*. It would parse the
wrapper's stderr, which reaches the console directly, and it cannot know the
refusal.

### D2. The validation run

The operator:

1. runs `-Install -StopMachine` in Windows PowerShell 5.1, then in
   PowerShell 7. Each run is one install, one setup from the installed copy,
   the stopped-machine refusals and the restart with `podman machine start`;
2. runs setup again with unrestricted networking, then `windows-validate.ps1`
   once in Windows PowerShell 5.1, for the unprepared restricted mode;
3. runs setup again with offline networking, so the machine ends as before.

Step 3 also checks D7 of the previous change: setup proposes `default` for
the endpoint after the unrestricted setup saved `local`.

### D3. Host CA trust with a Podman machine

The machine is the host for setup and sessions, so host CA trust uses a
bundle in the machine. The Windows certificate store reaches it only when
Podman imports it: `podman machine set --import-native-ca` (Podman 6.0 or
later) makes the machine import the CAs that Windows trusts at every start
and run `update-ca-trust`, so the machine's system bundle contains them. The
docs give the steps: stop the machine (the command fails while it runs), set
the option, start it, then run
setup and answer yes to host CA trust with the system bundle it proposes.
Nothing in the code changes: the CA selection is the Linux one.

Alternative considered: *setup reads the Windows store itself*. It would need
a Windows-side export and a file to keep in sync; Podman already does both.

## Risks / Trade-offs

- [A Linux user who exports `WRAPPER_WINDOWS_ENTRY` gets the Windows step.] →
  The variable is internal to the Windows path; the message changes, nothing
  else does.
- [`-StopMachine` ends running sessions and restarts the machine.] → The
  README of the operator bundle says so; a failed restart prints `wsl
  --shutdown`, then `podman machine start`.
- [The second `-Install` run overwrites the summary file of the first in the
  same edition, and the run of step 2 overwrites the 5.1 one.] → The README
  asks to copy each summary before the next run.
