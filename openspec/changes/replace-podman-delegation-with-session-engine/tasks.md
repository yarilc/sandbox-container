# Tasks

## 1. Session topology

- [x] 1.1 Validate design D1 before building on it.
  - **Setup:** with the spike engine configuration, start an engine with `--network=none`, then create a restricted fixture session with `--network container:<engine>` and its other `agent-args` options.
  - **Verify:** the guard bootstrap, proxy readiness and a fixed qualification run pass unchanged; `/etc/hosts` and `resolv.conf` match a session without an engine.
  - **Fallback:** if any check fails, switch the design to the `ns:` join with a namespace inode check, updating design D1 and these tasks.
  - **Record:** the outcome in `docs/validation.md`.

## 2. Engine image and setup preparation

- [x] 2.1 Add the shared engine build inputs under `launcher/engine/`.
  - **Contents:** a Containerfile `FROM quay.io/podman/stable@sha256:<digest>` and the replaced configuration of design D3: `containers.conf`, the deleted vendor and rootless drop-ins, an empty `mounts.conf`, and a probe rootfs directory for design D10.
  - **Registration:** add them to the installed manifest in `setup/common.py` and to the shared lists in `tests/test_alignment.py`.
  - **Verify:** `python3 -I setup/common.py --manifest` lists them, and `python3 -m unittest tests.test_alignment tests.test_image_pins` passes with the base pinned by digest.
- [x] 2.2 Make setup build the engine image in every mode, and generate the engine seccomp profile from the engine host's default (design D4).
  - **Record:** the image ID and the profile and source digests in the installation.
  - **Verify:** `tests/test_setup.py` cases for:
    - a fresh offline setup that builds both;
    - a rerun that reuses them;
    - a changed host default profile that regenerates the profile;
    - a failed engine build that leaves the last working installation selected.
- [x] 2.3 Establish the engine's minimal capability set (design D4).
  - **Verify:** nested rootless containers run with `--cap-drop=all --cap-add=SETUID,SETGID` and fail without either capability.
  - **Record:** the options in the engine argument builder and in `docs/validation.md`.
- [x] 2.5 Let the engine build images and extract new layers (design D4). Found after `sandbox-ref-29`: with `SETUID` and `SETGID` only, `podman build` failed at a `RUN` step and `podman load` of new layers failed, both on `chroot`.
  - **Verify:**
    - with `--cap-add=SETUID,SETGID,SYS_CHROOT`, a build with a `RUN` step and a load of new layers succeed in an engine started with the D4 options;
    - the qualification probe expects the bounding set `0x400c0`;
    - `SessionEngineTests` builds, saves, removes and loads an image in a session.
  - **Record:** `docs/validation.md`, under `sandbox-ref-30`.
- [x] 2.6 Pin the engine base to an `-immutable` tag (design D3). Found after `sandbox-ref-30`: a clean pull of the pinned `quay.io/podman/stable@sha256:3e54de04…` failed with `manifest unknown`, because quay.io had rebuilt `v6.2` and deleted that manifest. Installations that already had the base built the engine; a new one could not.
  - **Verify:**
    - the base resolves from quay.io by its pinned index digest;
    - Podman, crun and fuse-overlayfs keep the measured versions, and the files the recipe removes or empties exist;
    - `tests/test_engine.py` refuses a base without an `-immutable` tag;
    - the engine built on it passes the `session-engine` qualification case and `SessionEngineTests`.
  - **Record:** `docs/validation.md`, under `sandbox-ref-31`.
- [x] 2.4 Document the engine image in `docs/setup.md`: what setup builds, the seccomp derivation and when it is regenerated.
  - **Verify:** every documented command runs as written in a scratch installation.

## 3. Image toolchains

- [x] 3.1 Extend recipe validation in `setup/toolchains.py` with `images` (design D5, toolchain-library "Image entries in recipes").
  - **Accepted:** digest-pinned references, and local images given as a full `sha256:` ID plus a `localhost/` name. Image-only recipes are valid.
  - **Rejected:** tag-only references, and `PATH`, `env` or `default` without file sources.
  - **Verify:** `tests/test_toolchains.py` cases for each accepted and rejected form.
- [x] 3.2 Write images into `<library>/.images` through a helper container of the engine image, under the library lock.
  - **Pinned images:** pulled with the host network and CA trust.
  - **Local images:** `podman save`, then `load`, with the image ID checked after loading.
  - **Index:** new optional fields only; keep the schema number.
  - **Verify:** `tests/test_toolchains.py` cases with `tests/fake_podman.py`:
    - the helper's mounts are only the store and the CA bundle;
    - an `add` prints each image;
    - a local image with a different ID fails, leaving the library unchanged;
    - the index schema is unchanged.
- [x] 3.3 Implement reference-counted image deletion, and the refusal to delete while engines run (design D8).
  - **Verify:** `tests/test_toolchains.py` cases for:
    - a shared image kept until its last toolchain goes;
    - `remove` and a replacing `add` refused with a running engine (the message names the session);
    - an image-adding `add` allowed with a running engine.
- [x] 3.4 Run image recipe checks against a temporary engine without network (design D11).
  - **Verify:**
    - a `tests/test_toolchains.py` case for the assembled check, with no network, `container:` networking and `CONTAINER_HOST`;
    - a runtime case in `tests/test_network_runtime.py` where an image that needs network to start fails its check.
- [x] 3.5 List images in `toolchains.md`: the pinned reference, an example `podman run`, and the "sessions with an engine" note.
  - **Verify:** a `tests/test_toolchains.py` case for the rendered entry of an image-only toolchain and of a mixed one.
- [x] 3.6 Measure what a running nested container does when its image is removed from the store.
  - **Setup:** a runtime experiment through two engines on a scratch library.
  - **Record:** the result in `docs/validation.md` as input for a later relaxation of design D8; no code change.
- [x] 3.7 Check rollback compatibility.
  - **Verify:** the previous release's `--container-toolchain list` and `launch-env` work on a library with `.images` and image-only toolchains. Record the result, and fix the index if they fail.
- [x] 3.8 Document image recipes in the README "Managing the library" and "Recipes" sections: fields, local images, live updates, and removal while sessions run.
  - **Verify:** every command in those sections runs as written in a scratch library.
- [x] 3.9 Read engine labels in a form every Podman version accepts (design D8). Found after `sandbox-ref-31`, by the Claude adoption's Windows validation on a machine with Podman 6:
  - `--container-toolchain remove` failed with "cannot index slice/array with type string" whenever an engine was running;
  - the launcher's reconciliation of engines left by interrupted launches failed silently on the same template.
  - **Verify:**
    - with a Podman 6.2 client, `ps --format '{{index .Labels …}}'` fails, while `ps --format json` and `container inspect` with `{{index .Config.Labels …}}` work, as they do with the 4.3 client;
    - the fakes in `tests/test_toolchains.py` and `tests/fake_podman.py` refuse `.Labels` in `ps` templates, as Podman 6.2 does;
    - the engine-listing and reconciliation tests pass.
  - **Record:** `docs/validation.md`, under `sandbox-ref-32`.

## 4. Engine in sessions

- [x] 4.1 Extend `launch-env` to report the image store path and whether it holds images.
  - **Verify:** `tests/test_toolchains.py` cases for an empty store, a store with images, and the output parsed by the launcher.
- [x] 4.2 Start the engine in `launcher/core.sh` and `network/session.py` before creating the session.
  - **Engine:** as designed in D1, D4 and D6: labelled session volume, exact mounts and options, `127.0.0.1:2375` service plus an engine-side Unix socket, readiness query with a timeout.
  - **Session:** created with `--network container:<engine>`, `CONTAINER_HOST` and `DOCKER_HOST`, and a private
    read-only `/etc/hosts` filled between create and start (design D1).
  - **Verify:** `tests/test_launcher.py` cases with `tests/fake_podman.py` for:
    - the assembled engine and session arguments in each mode;
    - no engine without images or with `<P>_TOOLCHAINS=0`;
    - no host path beyond the workspace, the worktree parent, the store and the CA bundle.
- [x] 4.3 Tie the engine's lifecycle to the session.
  - **Behavior:** removed with its volume when the session ends; an engine start or readiness failure stops the launch before the application, leaving no resources; stale engines are cleaned by the existing reconciliation.
  - **Verify:** `tests/test_launcher.py` cases for normal exit, signals, failed start and a stale engine.
- [x] 4.4 Apply and verify the session budgets on the engine (design D7), with notices for unenforced budgets and for the doubled total.
  - **Verify:** `tests/test_launcher.py` budget cases for systemd-delegated controllers, cgroupfs and the rlimit fallback.
- [x] 4.5 Add runtime engine checks in `tests/test_runtime.py`, run by `bash tests/run-runtime.sh` with an image toolchain in a scratch library.
  - **Checks:**
    - offline run by index and platform digest;
    - no external path from nested containers;
    - private procfs and UTS;
    - the workspace bind works;
    - host paths outside the workspace show the engine's files;
    - empty `/run/secrets`;
    - two concurrent sessions are isolated;
    - a live-added image runs;
    - the store refuses removal;
    - the session storage is gone after exit.
  - **Verify:** `bash tests/run-runtime.sh` passes.
- [x] 4.6 Document the engine:
  - a README "Container tests" section covering when, endpoint, images, storage, budgets, exceptions and limits;
  - `docs/launcher-contract.md`;
  - `docs/launcher-test-map.md`.
  - **Verify:** the contract and test map entries name the new tests, and the README commands run as written in a session.

- [x] 4.7 Check a restricted session's interfaces in its network namespace (design D1). Found after `sandbox-ref-32`: the first setup with image toolchains on the Windows Podman machine failed its smoke check, because a session with an engine sees the host's `/sys` and its `/sys/class/net` lists the host's interfaces.
  - **Verify:**
    - nested containers that join another container's network namespace get their parent's `/sys`, with or without its user namespace, while `/proc/net/dev` shows only the shared namespace;
    - the setup smoke check, the qualification probe and the offline runtime tests read `/proc/net/dev`, and the offline engine test checks that it lists only loopback;
    - the README's engine section documents the host `/sys` view.
  - **Record:** `docs/validation.md`, under `sandbox-ref-33`.

## 5. Engine qualification

- [x] 5.1 Add the engine containment probe to restricted qualification (design D10).
  - **Probe:** `--rootfs` nested containers; route, procfs, UTS, secrets and read-only-store checks; engine options compared with D4.
  - **Identity:** bind the results to the engine image ID and seccomp profile digest.
  - **Gate:** require them for launches that start an engine.
  - **Verify:**
    - `tests/test_qualification.py` cases for a passing probe, a failing probe and a report without engine results;
    - `bash tests/run-runtime.sh --qualification`.
- [x] 5.2 Add engine containment to the network evidence: `docs/network-contract.md`, and the credential-free bypass list in `docs/validation.md`.
  - **Verify:** the documented checks map to the tests of tasks 4.5 and 5.1.

## 6. Delegation removal

- [x] 6.1 Remove delegation from `launcher/core.sh`:
  - socket selection and verification, the socket mount, the delegated `CONTAINER_HOST` and the client tmpfs mounts;
  - the help lines for `<P>_PODMAN` and `<P>_PODMAN_SOCKET`.

  Then add the leftover-opt-in refusal (container-launcher "Leftover delegation opt-in is refused").
  - **Verify:** `tests/test_launcher.py`:
    - delegation cases replaced by refusal cases (exact `1` in every mode and for build-only, other values ignored, help and toolchain commands unaffected);
    - no remaining mount of any Podman socket.
- [x] 6.2 Remove the delegation questions from `setup/setup.py`.
  - **Preferences:** bump the preferences schema, migrate `podman` and `delegation_socket` away with a notice, and make the managed launcher refuse preferences that still enable delegation.
  - **Verify:** `tests/test_setup.py` cases for a migrated rerun, a refused managed launch and a fresh setup without the question.
- [x] 6.3 Change the Windows shim's delegation refusal text to the common migration message, and keep the bootstrap's saved-delegation refusal.
  - **Verify:**
    - `bash tools/powershell.sh .`, with the shim tests updated;
    - `python3 -m unittest tests.test_windows_bootstrap`.
- [x] 6.4 Rewrite the delegation cases in `tests/test_runtime.py`, `tests/test_wrapper.py` and `tests/test_network_runtime.py` as refusal or engine cases.
  - **Verify:** `bash tests/run-runtime.sh` and `--wrapper` pass, and `grep -rn "_PODMAN_SOCKET\|podman.sock" tests/` finds only refusal checks.
- [x] 6.5 Remove delegation guidance from:
  - `README.md`;
  - `AGENTS.md` (Build, Testing and Security sections);
  - `docs/launcher-contract.md`, `docs/setup.md` and `docs/network-contract.md`.

  Add a migration note that points to image toolchains.
  - **Verify:** a repository grep for `SANDBOX_CONTAINER_PODMAN` finds only the migration note, the refusal code and its tests.

## 7. Repository tests from a session

- [x] 7.1 Let `tests/run-runtime.sh` run from inside a session against its engine. When the checkout is not on native storage, copy it into an engine volume, as the spike driver did.
  - **Verify:** every `run-runtime.sh` mode, `bash tools/shellcheck.sh .` and `bash tools/powershell.sh .` run from a restricted session with the needed images in the library.
- [x] 7.2 Fix `test_term_forwarding` in `tests/test_launcher.py`: it must fail when `.started` never appears, and wait longer than 2 s.
  - **Verify:** 20 consecutive runs pass inside the engine.

## 8. Integration validation

- [x] 8.1 Run all suites from a restricted session on the Windows Podman machine, through the engine, and record the results in `docs/validation.md`.
  - **Expected machine-equivalent failures:** the cgroupfs budget subtests and the AF_VSOCK control.
  - **Expected engine-only failures:** the 3 guard tests with explicit limits.
- [ ] 8.2 On a native Linux host with the systemd cgroup manager, verify:
  - the engine budgets are enforced;
  - an offline session runs a library image;
  - whether nested explicit limits apply (design Open Questions).
  - **Record:** both in `docs/validation.md`.
- [x] 8.3 From Windows, validate:
  - an offline session with an image toolchain;
  - the `<P>_PODMAN=1` refusal;
  - a setup rerun over saved delegation.
  - **Record:** the cases in `tools/windows-validate.ps1` and `docs/validation.md`.
- [x] 8.4 Run the repository checks:
  - `openspec validate replace-podman-delegation-with-session-engine --strict`;
  - `bash tools/shellcheck.sh .` and `bash tools/powershell.sh .`;
  - `python3 -m unittest discover -s tests`;
  - `git diff --check`.

  All must pass.

## Workflow follow-up

- Tag the release and propagate the shared files to the sibling wrappers with `tools/propagate.py` (dry run, then `--apply`), following `docs/propagation.md`.
- Archive the change after review, syncing the specs and retiring `container-podman-access`.
