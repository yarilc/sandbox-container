# Design

## Context

**Starting an engine.** `setup/engine.py` `container_options()` builds the
options for every engine:
- the session's engine (`launcher/core.sh`);
- the qualification probe engine (`network/qualify.py`).

The options include `--cap-drop=all --cap-add=SETUID,SETGID,SYS_CHROOT,CHOWN`,
as `support-nested-systemd-containers` (merged on 2026-11-26) set them. The
engine's startup program starts as the root of its user namespace, delegates
the engine's cgroup subtree with `CHOWN`, and runs everything else as the
engine user with the other three capabilities. Qualification checks PID 1's
state: `CapBnd: 00000000000400c1` (the four), and the other three in its
permitted, effective and ambient sets (`00000000000400c0`).

**The recipe.** `launcher/engine/Containerfile` has no `LABEL`. The image
therefore inherits the base's label:

```
io.containers.capabilities=CHOWN,DAC_OVERRIDE,FOWNER,FSETID,KILL,NET_BIND_SERVICE,SETFCAP,SETGID,SETPCAP,SETUID,SYS_CHROOT
```

The operator confirmed this label on the Rocky 9 lab host.

**What Podman does with the label.** Podman first computes the container's
capabilities from its defaults and the options. It then compares the label
with them:
- **Label within that set:** the container gets the label's capabilities.
- **Label outside that set:** Podman logs `Capabilities requested by user or
  image are not allowed by default` with the capabilities it is missing, and
  keeps its own set.

The recorded error lists exactly the eight capabilities that the options
removed before `CHOWN` was added; the same engine start now names seven.

**Where the message appears.** Podman logs it where the container is created:
- with the local client, as in an unrestricted session from a checkout, in
  the session's terminal;
- through a Podman service, in the service's log.

That is probably why the reference's offline session on the same host showed
no error.

**Build inputs.** The recipe is an engine build input
(`setup/engine.INPUTS`): setup rebuilds the engine image when the recipe
changes. It is also a qualification input (`network/qualification_records.py`).

## Goals / Non-Goals

**Goals:**
- An engine starts without the capability error, with an unchanged bounding
  set.
- The label cannot drift from the launcher's options without a failing shared
  test.

**Non-Goals:**
- **No change to the engine's privileges**, and no other change to the
  hardening exceptions.
- **No new runtime assertion on the error text.** The runtime runner reaches
  Podman through its service, where the message never reaches the test's
  output. The evidence comes from the operator's direct Podman runs on the
  hosts (decision 4).
- **No change to `tools/propagate.py`.** Its checklist does not map the
  engine recipe to runner modes. The modes this change needs are listed in its
  tasks, and the wrappers' adoptions run every mode anyway.

## Decisions

1. **The recipe sets the label to the launcher's set.**
   - **How:** `LABEL io.containers.capabilities="SETUID,SETGID,SYS_CHROOT,CHOWN"`
     in `launcher/engine/Containerfile`, beside `USER podman`, with a
     comment naming `container_options()`. Podman then finds the label within
     its computed set, and gives the engine the same four capabilities
     without an error.
   - **Alternatives rejected:**
     - Silencing Podman, with `--log-level` or a `containers.conf` setting:
       it would also hide real errors.
     - An empty label: Podman reads it as no capabilities at all, and the
       engine would lose the four it needs.
     - A label of the three capabilities that the engine user keeps: Podman
       would narrow the engine to the label, and the startup program would
       lose `CHOWN`.
     - Granting the capabilities through the label instead of the options:
       the options are the documented exceptions, which tests and
       qualification check.
     - Documenting the message only: every engine start would still report
       an error.

2. **The options stay the single source.** The shared recipe check in
   `tests/test_engine.py` reads the label from the recipe and compares it
   with the `--cap-add=` value of `engine.container_options()`. A second
   check makes sure that a recipe without the label fails, and so does one
   with a wider or a narrower label. The check caught the drift when this
   change was rebased on `support-nested-systemd-containers`.

3. **The README names the label.** The hardening exceptions paragraph says
   that the engine image declares the same four capabilities. The paragraph
   on shell containers is unchanged.

4. **Host evidence compares both images, with the local client.**
   - **The comparison:** on each native host, the operator builds the
     branch's recipe twice: once with the label line removed, once as it is.
     Only the label differs. They start both images with the engine's
     capability options, and print `CapBnd` from `/proc/self/status`.
     - **Expected:** the image without the label logs the error, at least
       with Podman 5.8.0. The new image logs nothing. Both report
       `00000000000400c1`.
   - **The session:** an unrestricted session that starts an engine,
     opened from the branch on the Rocky 9 lab host, shows no error.
   - **The runner:**
     - the default runtime mode (`SessionEngineTests`), `--network` and
       `--qualification` pass with the rebuilt image;
     - the qualification engine case checks the capability sets again.

5. **One new tag with `support-nested-systemd-containers`, in the usual procedure.**
   - **Scope:** `sandbox-ref-36` carries both changes. That change's own
     host validation is in its record; this change's runs repeat the modes
     that exercise the engine, with both changes in the image.
   - **Before tagging:** the recipe is a qualification input, so
     `--qualification` must pass (`reference-propagation`, "Reference runs
     the adoption suites before tagging"), and so must the shared suite.
   - **On the main branch:** the reference parity cell moves to
     `sandbox-ref-36` in the merge that the tag points to.

## Risks / Trade-offs

- **[Risk] A Podman version treats the label differently** and gives the
  engine more than the options. → Qualification fails closed on any other
  `CapBnd`, and the host comparison covers Podman 4.9.3 on WSL and 5.8.0 on
  Rocky.
- **[Risk] Disk space on the Rocky lab host.** → The new image differs only
  in its configuration and shares every layer with the current one. The
  operator checks the free space before building.
- **[Trade-off] Existing installations keep the message** until their wrapper
  adopts the tag and setup rebuilds the engine image. It stays harmless
  meanwhile, as the Context explains.

## Migration Plan

- **Wrappers:** each adopts `sandbox-ref-36`, and its operators rerun
  `--container-setup`. Setup rebuilds the engine image, because its build
  inputs changed, and requalifies the installation.
- **Rollback:** revert the merge and rerun setup; the previous image comes
  back with the message.
