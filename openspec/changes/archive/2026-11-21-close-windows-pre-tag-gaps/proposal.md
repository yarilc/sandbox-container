# Proposal

## Why

Three Windows items remain before the branch is tagged `sandbox-ref-27` and
propagated to the agent wrappers. Fixing a shared file after the tag would
need another tag and another propagation.

- From Windows, an agent wrapper cannot receive its API key. The Claude
  profile's `api` method reads `ANTHROPIC_API_KEY` at launch. On Linux the
  variable is in the launcher's environment. The Windows shim forwards only:
  - `<P>_*`;
  - the configuration-directory variable;
  - the approval-bypass variable;
  - the names in `<P>_ENV_VARS`.

  So `$env:ANTHROPIC_API_KEY` never reaches the machine. The reference profile
  has no authentication method, so no reference test showed it.
- The `local` endpoint has never run from Windows. The first validation run of
  `validate-windows-remaining-cases` failed "One engine for sessions and the
  machine" on a release that an earlier setup in a Linux shell of the machine
  had saved. A setup that misses the machine's service saves unrestricted
  networking with the `local` endpoint. The later Windows runs all used
  `default`.
- Bitdefender's Advanced Threat Control blocks the operator validation script
  and quarantined files while validation bundles were extracted. Setup, the
  installer and sessions ran with it active, and another Windows system with
  other antivirus products showed no problem. The README describes it only as
  a quarantine during clone or extraction.

## What Changes

- **Credential variables from Windows.** The entry also forwards, by name,
  every `credential_env` that the profile's authentication methods declare,
  as it forwards the approval-bypass variable. The launcher keeps passing
  only the selected method's credential to provider sessions.
- **The `local` endpoint from Windows, reproduced.** The operator runs these
  on Windows:
  - an unrestricted setup with the `local` endpoint, then `windows-validate`;
  - a setup in a shell opened with `wsl -d podman-machine-default`, then
    `windows-validate`;
  - a final offline setup, which also checks that `default` replaces a saved
    `local`.

  A failure stops the change for a decision (design D2) before the tag.
- **Antivirus documented.** The README's Windows limits, the header of
  `tools/windows-validate.ps1` and `docs/validation.md` describe the observed
  behavior:
  - only with Bitdefender;
  - only with the validation script and bundle extraction;
  - the workaround: exclude the folder or pause the protection, as the
    administrator allows.

  No code changes for it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `windows-launcher`: "Environment forwarded by name to the distribution"
  also forwards the profile's credential variables.

## Impact

- `launcher/windows/core.ps1` (shared): the forwarded names.
- `tests/windows/shim_tests.ps1`: cases for the credential variable, with the
  fixture agent profile (`FIXTURE_API_KEY`).
- `README.md`, `docs/launcher-contract.md`, `docs/validation.md`,
  `tools/windows-validate.ps1` (header comment).
- Possibly `setup/` or `launcher/windows/` if the `local` reproduction fails
  (design D2).
- These changes join the same reference tag as the other Windows changes.
