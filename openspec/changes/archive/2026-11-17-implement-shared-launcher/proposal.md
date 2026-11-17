# Proposal

## Why

`docs/launcher-contract.md` (archived change `define-launcher-contract`) fixes the target behavior of every launcher, the shared-core contract and the spec deltas, with decisions U1-U18. Today each wrapper still carries its own 900-1,250-line launcher and 1,500-1,900-line `tests/test_wrapper.py`, so each launcher defect is ported up to six times. This change builds the shared core in the reference, so the five agent wrappers can then adopt it by tag.

## What Changes

- New shared `launcher/core.sh`: the complete launcher of the contract (phases 1-7, core rules and decisions U1-U18), written once and agent-neutral.
- `sandbox-container.sh` becomes the thin entry script of the contract; the reference's `agent/launcher.sh` carries its profile data (a shell profile, no hooks).
- New shared `tests/fake_podman.py` (the union fake engine) and `tests/test_launcher.py` (the shared launcher tests, run against two fixture agent parts: `tests/fixtures/agent/launcher.sh` with every hook and `tests/fixtures/shell-agent/launcher.sh` with none). The reference's `tests/test_wrapper.py` keeps only tests specific to the reference shell.
- Shared code learns the core:
  - `setup/common.py` installs `launcher/core.sh` and `agent/launcher.sh`; setup always builds through the wrapper; setup and smoke drop `ENV_VARS` and `READONLY_STATE`;
  - `network/qualification_records.py` and `network/control.py` bind and protect the core files; `setup/launch.py` trusts them;
  - `network/qualify.py`, `network/qualification_records.py` and `setup/common.py` derive a missing network mode from the profile;
  - `network/agent_profile.py` accepts `native.exec` and `native.exec_tmp`, drops `install.runtime_build` and knows the new variable suffixes.
- **BREAKING** for the reference launcher (no release yet, so no compatibility handling):
  - `--container-build` without application arguments builds and exits;
  - one temporary-storage layout (512 MiB `/tmp` and `/var/tmp`, 32 MiB `/run`, 512 MiB tmpfs home);
  - stale images are refused;
  - new `<P>_ENV_VARS` and `<P>_READONLY_STATE`;
  - locale and, in unrestricted mode, proxy variables are forwarded;
  - `--init` and `CONTAINER_NAME` in sessions.
- The shared directories gain `launcher/`, and the shared tests gain `tests/test_launcher.py` and `tests/fake_podman.py`. The change ends with the annotated tag `sandbox-ref-22`.

## Capabilities

### New Capabilities

- `shared-launcher`: one shared Bash core sourced by a thin entry script, a per-agent `agent/launcher.sh` with profile data and bounded hooks, the common option and variable interface, and the shared launcher tests on a shared fake engine.

### Modified Capabilities

- `container-launcher`: image operations (build-only, freshness, build format), engine verification and query timeouts, invocation and environment (shell profiles, locale, proxy, credentials, `<P>_ENV_VARS`), owned lifecycle (`--init`, `CONTAINER_NAME`, owned name after a failed create), qualification with the resolved mode.
- `container-isolation`: temporary-storage layout and the profile's executable-temporary-storage flag.
- `persistent-state`: tmpfs home below shared state, read-only state, lexical and containment checks.
- `container-setup`: installation contents and setup builds through the wrapper.
- `network-egress`: qualification and preflight bind the core files; profile fields; disclosure printed from the policy.
- `container-podman-access`: delegated sessions get private tmpfs mounts for nested Podman storage.
- `reference-propagation`: a shared directory new in the adopted tag is adopted with it.

## Impact

- Reference only: `sandbox-container.sh`, new `launcher/`, `agent/launcher.sh`, `agent/profile.json`, `setup/`, `network/`, tests, fixtures, README, `docs/` and specs. New tag `sandbox-ref-22`.
- No wrapper repository changes here. Each wrapper adopts `sandbox-ref-22` in its own change (Claude; then Codex, Antigravity and Pi; then OpenCode), moving its behavior into `agent/launcher.sh` and its hook tests.
- Installations need a new setup: the installed and qualified code changes.
