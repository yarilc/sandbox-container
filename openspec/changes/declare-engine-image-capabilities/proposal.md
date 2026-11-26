# Proposal

## Why

When the launcher starts a session container engine, Podman prints:

```
ERRO … Capabilities requested by user or image are not allowed by default:
"CAP_CHOWN,CAP_DAC_OVERRIDE,CAP_FOWNER,CAP_FSETID,CAP_KILL,CAP_NET_BIND_SERVICE,CAP_SETFCAP,CAP_SETPCAP"
```

Claude's `adopt-sandbox-ref-35` validation recorded this error in an
unrestricted session on the Rocky 9 lab host (Podman 5.8.0).

The cause is the engine image's base. `quay.io/podman/stable` labels itself
`io.containers.capabilities=CHOWN,DAC_OVERRIDE,FOWNER,FSETID,KILL,NET_BIND_SERVICE,SETFCAP,SETGID,SETPCAP,SETUID,SYS_CHROOT`,
which the operator confirmed on that host. `launcher/engine/Containerfile` keeps
the label. The launcher starts the engine with `--cap-drop=all
--cap-add=SETUID,SETGID,SYS_CHROOT`. Podman sees the label asking for eight
capabilities that the options removed. It logs an error and keeps the
launcher's set.

The engine's capabilities are therefore already right: qualification checks
that its bounding set is exactly `SETGID`, `SETUID` and `SYS_CHROOT`. But every
engine start reports an error that is not one, in the terminal of a session
that uses the local Podman, such as an unrestricted session.

Codex, Antigravity, OpenCode and Pi have not adopted `sandbox-ref-35` yet. A
tag now lets them adopt the fix in the same step.

## What Changes

- **The engine image declares its capabilities.** `launcher/engine/Containerfile`
  sets `io.containers.capabilities` to `SETUID,SETGID,SYS_CHROOT`, the set the
  launcher grants (`setup/engine.py`).
  - Podman then finds nothing to refuse and prints no error.
  - The engine runs with the same three capabilities as today.
- **A shared test keeps the label and the options together.** The engine
  recipe check in `tests/test_engine.py` fails when the label differs from the
  capabilities of the engine options.
- **README.** The hardening exceptions name the label.
- **New reference tag `sandbox-ref-36`.**
  - **Before tagging:** the reference runs the modes the propagation rules
    require. The recipe is a qualification input, so `--qualification` is one
    of them.
  - **On both native hosts:** an engine started from the new image prints no
    capability error and keeps the same bounding set.
- **Installations:** the engine's build inputs change. A wrapper that adopts
  the tag rebuilds its engine image on its next `--container-setup`. An
  installation that has not rerun setup keeps the old image, and still prints
  the message.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `session-container-engine`: the new requirement "Engine image declares its
  capabilities". The engine image's capability label equals the capabilities
  the engine runs with, so that starting the engine reports no capability
  error.

## Impact

- **Shared files:**
  - `launcher/engine/Containerfile`, a qualification input and an engine
    build input;
  - `tests/test_engine.py`.

  The README is this repository's own. Each wrapper updates its README when
  it adopts the tag.
- **Images:** the engine image ID changes, so its qualification is redone.
  The base image and its digest are unchanged, so the image pins procedure in
  `docs/validation.md` does not apply.
- **Wrappers:**
  - Claude adopts `sandbox-ref-36` in its own change;
  - Codex, Antigravity, OpenCode and Pi adopt it directly from
    `sandbox-ref-28`.
- **Validation:**
  - **Here:** the shared suite.
  - **On the Rocky 9 lab host and on WSL, from the branch:**
    - the runtime, `--network` and `--qualification` modes;
    - a comparison of engine starts with the current and the new image;
    - an unrestricted session that starts an engine.
