## Context

See proposal.md, section Why. The pin lives only in this repository's
`Containerfile`. The file is not a propagated reference copy: wrappers own
their `Containerfile`. The bump therefore needs no tag and no propagation.

`docs/validation.md`, section "Updating pinned image inputs", gives the procedure:

1. edit the pin;
2. run `test_image_pins.py`;
3. rebuild under maintenance authorization and check the version;
4. the operator reruns setup;
5. record a dated entry.

The reference image has no agent CLI, so there is no endpoint inventory to
revalidate. `tested.cli` in `agent/policies/default.json` stays
`none (Bash shell; no agent CLI)`.

The launcher mounts `~/.config/openspec` read-write as shared persistent state,
so the image's OpenSpec reads whatever an earlier release wrote there.

## Goals / Non-Goals

**Goals:**
- Pin `@fission-ai/openspec@2.0.0` exactly. The existing pin tests and the
  image smoke check must pass unchanged in meaning.
- Show that OpenSpec 2.0.0 works inside the image as a planning tool:
  - offline under the guard;
  - with state that 1.16.0 left in `~/.config/openspec`.

**Non-Goals:**
- Changing the base image digest. A separate sandbox-image change will do that.
- Migrating the operator's workspace commands (`/opsx:*`) or running
  `openspec update` in any repository. That step comes last, outside the changes.
- Any wrapper repository.

## Decisions

- **Version 2.0.0, not 2.1.0.**
  - The rule agreed on 2026-11-18 takes the newest non-prerelease that was at
    least 72 hours old. 2.1.0, published 2026-11-17, fails it.
  - 2.1.0 also needs Git and GitHub access to install skills, which an offline
    session does not have.
  - Alternative considered: 1.17.0. It keeps the `/opsx:*` commands, but the
    user chose 2.0.0.
- **No spec delta (`skip_specs: true`).**
  - The `runtime-image` requirement is about an exact recorded version, not
    about a particular one.
  - A version-specific requirement would add nothing that the pin tests do not
    already enforce.
- **Functional check beyond `--version`.**
  - The major release changed skill generation and cleanup. So the record also
    includes a planning round trip inside the image, run in offline mode on a
    temporary project: `openspec init --tools none` (or the 2.0 equivalent),
    `openspec new change`, `openspec validate --all`, `openspec list --json`.
  - The test suite does not gain this check. It is a one-time maintenance check,
    and a permanent test would need the image in the unit suite.
- **Unchanged node base.**
  - OpenSpec 2.0.0 declares `node >=22.12.0`, the same as 1.16.0.
  - The pinned `node:22-bookworm-slim` already satisfies it.

## Risks / Trade-offs

- [OpenSpec 2.0 may rewrite or reject files left by 1.16.0 in
  `~/.config/openspec`] → Start the new image against an existing state
  directory and confirm `openspec --version` and the round trip succeed.
  Record what changed in the directory.
- [2.0.0 may try to reach the network at start, for example for an update
  check or telemetry] → The round trip runs in offline mode, where egress is
  denied. It must still complete. Any attempt the guard reports is recorded in
  the validation entry.
- [2.0.0 is a major release] → Rollback is a one-line revert of the pin
  followed by a rebuild. No state migration is needed, because 2.0.0 is
  expected to leave state as 1.16.0 left it; the first risk confirms it.

## Migration Plan

1. The operator pushes `main`.
2. The operator runs `--container-setup` on the three hosts, because the image
   identity changes.

The wrapper changes follow, each in its own repository.
