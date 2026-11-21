# Design

## Context

- The shim builds the forwarded set in `launcher/windows/core.ps1` (design D4
  of `support-windows-podman-machine`):
  - `<P>_*` except `<P>_WSL_*`;
  - `config_dir_env`;
  - `approval_bypass_env`;
  - the names in `<P>_ENV_VARS`, minus the reserved names and prefixes.

  Each nonempty value crosses with `/u` in `WSLENV`.
- The profile declares a method's key variable as
  `auth.<method>.credential_env`. Claude's is `ANTHROPIC_API_KEY`; the fixture
  agent's is `FIXTURE_API_KEY`.
- In provider mode the core passes `--env <credential>` only for the selected
  policy profile (`selected_credential`). It reserves the other methods'
  variables, so a listed one is skipped with a notice.
- From the bootstrap, `launcher/windows/enter.sh` writes the environment to a
  mode-0600 file in `/run/user/<uid>/windows-entry`. That directory is a tmpfs.
  The inner part reads the file and removes it.
- Setup on Windows runs in the machine's systemd namespaces and finds the
  service, so it proposes the `default` endpoint. A setup outside those
  namespaces finds no service. It then offers only unrestricted networking,
  with the `local` endpoint.

## Goals / Non-Goals

**Goals:**

- A Windows user supplies an API key as on Linux: `$env:ANTHROPIC_API_KEY`,
  then the entry.
- Before the tag, know whether sessions from Windows work with a release that
  uses the `local` endpoint, or one that a Linux shell set up.

**Non-Goals:**

- The account login flow on Windows (`claude auth login --claudeai` in the
  machine). It belongs to the provider check in an agent wrapper after
  propagation.
- Forwarding other agent variables (`protected_env`), which the core sets or
  refuses.
- Any antivirus workaround in code.

## Decisions

### D1. Forward the profile's credential variables by name

The shim reads every `auth.<method>.credential_env`. It validates each name
with the same variable-name rule as the other profile names; an invalid
profile stops the entry, as for the other fields. The shim adds the names to
the forwarded set next to the approval-bypass variable. It forwards all the
methods' variables, not only the selected method's, because:

- the shim does not know the method that setup saved;
- on Linux every variable is in the launcher's environment, and the core
  already passes only the selected one and reserves the others.

Like every forwarded name, a variable goes only with a nonempty value. A
credential name that matches a reserved name or prefix is not forwarded and
gets one notice, as for `<P>_ENV_VARS`. The help's Windows part names the
forwarded credential variables when the profile has them.

Alternative considered: *document `<P>_ENV_VARS=ANTHROPIC_API_KEY`*. It differs
from Linux. It relies on the core not reserving the selected credential, and
users would have to know the variable's name.

### D2. Reproduce the `local` endpoint on Windows, then decide

The operator runs these with the branch snapshot and records each summary:

1. From Windows, a setup with unrestricted networking and the endpoint
   answered `local`, then `windows-validate.ps1` (5.1).
2. From a shell opened with `wsl -d podman-machine-default`: first record
   `cat /proc/1/comm` and `echo $XDG_RUNTIME_DIR`, then run
   `bash /mnt/c/Work/sandbox-container/sandbox-container.sh --container-setup`,
   accept the proposed answers, and record the setup output. Then run
   `windows-validate.ps1` (5.1) from Windows.
3. From Windows, a setup with offline networking. It must propose `default`
   over the saved `local`. Then `-c 'echo ok'` from a project folder.

Decision rule:

- **Every case passes:** record the results; the earlier failure stays
  explained only by that unknown release, and nothing changes.
- **Step 1 fails:** sessions from Windows break with `local`. Apply pauses
  and the change is updated to choose one of two fixes:
  - setup started by the Windows entry (`WRAPPER_WINDOWS_SETUP`) stops
    offering `local`;
  - the `local` path is made to work.
- **Only step 2 fails:** the cause is a setup outside the namespaces. Apply
  pauses and the change is updated to choose one of two fixes:
  - setup in a Podman machine distribution refuses to run outside systemd's
    namespaces, and names the Windows entry or a login shell;
  - the bootstrap refuses such a release.

### D3. Antivirus, documented only

The README's Windows limits replace the current bullet with the observed
facts:

- Bitdefender's Advanced Threat Control (`Atc4.Detection`) blocked
  `tools/windows-validate.ps1`, and quarantined files while validation bundles
  were extracted with `tar`;
- setup, the installer and sessions ran with it active;
- another Windows system with other products showed no problem;
- the workaround: exclude the checkout folder, or pause the protection for the
  run, as the administrator allows; restore quarantined files; report the
  false positive.

`tools/windows-validate.ps1` gets the same advice in its header comment, and
`docs/validation.md` records the operator's report.

## Risks / Trade-offs

- [The API key crosses `WSLENV` and briefly lies in the helper's environment
  file.] → It is the same key the launcher reads on Linux. The file is
  mode 0600 on the user's tmpfs runtime directory, and the inner part removes
  it before the command runs. The key never reaches a command line.
- [A key set in PowerShell for another tool reaches unrestricted sessions.] →
  The same holds on Linux. The core passes it to the container only in
  provider mode, unless the agent part's hooks pass it.
- [The reproduction needs three setups on Windows.] → They reuse the
  prepared images. The final offline setup leaves the machine as it was.
