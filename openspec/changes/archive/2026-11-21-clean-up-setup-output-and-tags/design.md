# Design

## Context

- Setup prints `path_guidance()` twice: in the plan, then after `Sandbox:
  ready`, together with "Launch from a workspace: <command>" and
  "Review/change setup: <command> --container-setup". On Linux that is the
  right next step.
- The Windows shim starts setup with `wsl.exe ... --exec /bin/bash
  <wrapper> --container-setup`, with `WSLENV` cleared, so nothing tells setup
  where it was started from. Then the shim prints its own next step.
- `prepare_artifacts()` gives every candidate release its own tags,
  `PROFILE.image(<kind>, 'setup-' + <release id>)`, for the runtime image (a
  new tag on a reused image, or a build) and, in restricted modes, the
  toolchain and proxy builds. `setup.json` names the runtime tag, and launches
  use it. When the candidate is not activated, `main()` removes its release
  folder in `finally`, and the tags stay.
- Several installation roots of one wrapper share the image repository
  `localhost/<name>`. The disposable installations of `--setup-runtime` are an
  example. A tag that one root's releases do not name may belong to another
  root.

## Goals / Non-Goals

**Goals:**

- A setup run from Windows prints no Linux shell advice.
- A run that does not activate its candidate leaves no new tag behind.

**Non-Goals:**

- Pruning retained releases or their tags. Rollback depends on them.
- Detecting and removing tags left by earlier runs. That is documented as a
  manual step instead.
- Removing images. A run removes only the names it created.

## Decisions

### D1. Windows marker variable

The shim runs both setup calls (`--container-setup`, and the setup after an
install) with `WRAPPER_WINDOWS_SETUP=1`, forwarded as
`WSLENV=WRAPPER_WINDOWS_SETUP/u`. The `WRAPPER_WINDOWS_` prefix is reserved,
so the shim never forwards a user value under that name. Setup checks for the
exact value `1`. With it, setup:

- skips both `path_guidance()` calls and the two managed-command lines;
- prints `Start sessions with the Windows entry from a project directory on a
  Windows drive.`

The entry's own message then gives the exact command.

Alternatives considered:

- *Detecting WSL or a drvfs checkout.* It would also hide the guidance from
  Linux users who run setup from a WSL distribution, for whom it is correct.
- *A setup command-line flag.* It would add a flag to the shared Bash entry,
  and to every wrapper's help, for a Windows-only purpose.

### D2. Owned tag cleanup

`prepare_artifacts()` records in a list each tag it creates for the
candidate. The list holds the runtime tag (whether from `podman tag` or a
build), and the toolchain or proxy tag when it builds one. In `main()`'s
`finally`, when the candidate was not activated, setup:

1. for each recorded tag, reads the image ID, then runs
   `podman untag <tag> <tag>`, which removes only that name;
2. reads the image's remaining names;
3. reports each image left without a name as an effect, with
   `podman image rm <id>`;
4. reports an untag failure as an effect too. A failure does not hide the
   primary error.

The tags contain the candidate's own random release ID, so they cannot belong
to another root, another release or an earlier run. Cleanup runs in the same
`finally` as the folder removal, so it covers errors, cancellation, Ctrl+C,
SIGTERM and SIGHUP. Like the folder removal, it does not cover SIGKILL.

Alternative considered: *scanning for `setup-*` tags that no release of this
root names.* It would remove tags that other roots' releases still use.

### D3. Manual removal of earlier tags

`docs/setup.md` lists the steps:

1. list the `setup-*` tags with `podman images`;
2. collect the `image` values from `setup.json` of every release, in every
   installation root;
3. untag only the tags that none of them names.

## Risks / Trade-offs

- [The setup runs in the validation and earlier rounds already left tags.]
  → They are removed by hand, following D3. They are not reachable
  automatically without the risk described in D2.
- [An untag removes the last name of a freshly built image.] → The image stays
  and is reported with its removal command. Setup deletes no images.
- [Interruption during cleanup.] → Each untag is a short setup-owned command
  with the existing bounded teardown. A tag that remains is reported.
