# Tasks

## 1. Authentication guidance from the Windows entry

- [x] 1.1 In `setup/setup.py`, give `authenticate()` the Windows guidance of design D1 when `windows_entry()` is true. Verify: new `tests/test_setup.py` cases with the fixture profile and `WRAPPER_WINDOWS_SETUP=1`:
  - a declined login prints `<name>.ps1` with the login arguments and no distribution path;
  - an interactive method prints `<name>.ps1`;
  - the API method prints `$env:<KEY>`;
  - an argument with a space or a quote is single-quoted for PowerShell.

  The existing Linux cases still pass. `--setup` passes.
- [x] 1.2 Document the Windows authentication steps in `docs/setup.md` (Windows section). Verify: the section names `<name>.ps1 <login args>` and `$env:<KEY>`.

## 2. Reference tools

- [x] 2.1 In `tools/windows-validate.ps1`, add `--container-shell` to the command cases when the profile's `native.command` is not `bash` (design D2). Verify:
  - PSScriptAnalyzer passes;
  - a dry run against the fake `wsl.exe`, with a checkout copy whose `agent/profile.json` is the fixture agent profile, decodes `--container-shell` as the first argument of the command cases;
  - a dry run with the reference profile does not.
- [x] 2.2 In `tools/propagate.py`, recognize `== --mode` followed by `||` (design D3). Verify: a `tests/test_propagate.py` case with Claude's runner form finds `--guard` and `--guard-idle`. The dry run to `../claude-container` lists `--guard`.

## 3. Checks and tag

- [x] 3.1 Run `--shared`, `--setup`, `--setup-runtime`, `bash tools/shellcheck.sh .`, `bash tools/powershell.sh .` and `git diff --check`. Verify: the results are recorded in `docs/validation.md` under a section that names `sandbox-ref-28`. The only failures are the known environment ones.
- [x] 3.2 Merge into `main`, set the reference parity cell to `sandbox-ref-28`, and create the annotated tag `sandbox-ref-28` on the merge commit. Verify: `git tag -n1 sandbox-ref-28` names the merge commit, and `docs/network-contract.md` names the tag.

## Workflow follow-up

- Archive the change and sync its specs. The operator pushes `main` and the tag.
- Then apply `adopt-sandbox-ref-28` in `claude-container`.
