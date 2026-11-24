# Proposal

## Why

Agents cannot run tests that need containers without host authority. Podman
delegation mounts the host API socket, which:
- grants every mount and container of the service user;
- works only in unrestricted mode, because it bypasses egress enforcement;
- is unavailable on Windows.

A spike ran this repository's complete runtime suites from a restricted
session through a private nested Podman engine joined to the session's network
namespace. That engine held no secrets and had no host socket. Every suite
passed except checks that also fail on the Podman machine, or that need cgroup
limits the nested engine cannot apply. The private engine can therefore
replace delegation, in every network mode and on Windows.

## What Changes

- **Session container engine.** Every wrapper gives a session a private,
  rootless Podman engine when the toolchain library holds at least one image:
  - it shares the session's network namespace and inherits its egress boundary
    (offline stays offline);
  - the session reaches it at a loopback TCP endpoint through `CONTAINER_HOST`,
    and through `DOCKER_HOST` for Docker-API clients such as Testcontainers;
  - its writable storage belongs to the session and is removed with it;
  - it mounts the workspace at the same absolute path and no other host path,
    except the library's read-only image store;
  - it carries no secrets and has no host socket;
  - it receives the session's resource budgets.
- **Engine image.** Setup builds the engine image from a digest-pinned
  `quay.io/podman/stable` with the configuration verified in the spike:
  - an init process that reaps zombies;
  - a private procfs and private UTS namespace for nested containers;
  - file logging;
  - no mounts passed through from the engine host;
  - a masked secrets directory.

  The engine container is the one documented exception to the standard
  hardening of shell containers: nested containers need user-namespace helpers,
  FUSE, TUN, an unmasked procfs and `sethostname`.
- **Images as toolchains.** A recipe can list images in addition to, or instead
  of, file sources:
  - digest-pinned OCI references, or a local image pinned by image ID;
  - `add` pulls or copies them into an image store inside the library, through
    a helper container of the engine image, with the host's network and CA
    trust;
  - every engine mounts that store read-only as an additional image store, so
    images run offline by digest, and images added while a session runs become
    usable without a restart;
  - `toolchains.md` lists each image with its exact reference;
  - `verify` and `add` check image recipes inside an engine without network;
  - `remove` deletes images from the store; its behavior while a container uses
    an image is settled by a spike.
- **BREAKING: Podman delegation is removed.**
  - The launcher no longer mounts the host API socket into any session;
    `SANDBOX_CONTAINER_PODMAN` and `SANDBOX_CONTAINER_PODMAN_SOCKET` lose their
    meaning.
  - An exact `SANDBOX_CONTAINER_PODMAN=1` left in the environment, or saved
    delegation preferences, stop the launch with migration guidance (images in
    the toolchain library, then setup), on Linux and on Windows.
  - Setup no longer asks about delegation and migrates saved preferences
    without it.
  - The private tmpfs mounts for the delegated client storage are removed.

## Capabilities

### New Capabilities

- `session-container-engine`: covers the private per-session engine:
  - when it starts and how it attaches to the session's network;
  - the endpoint the session receives;
  - its mounts, image sources, storage lifecycle, budgets and hardening
    exceptions;
  - its cleanup and qualification.

### Modified Capabilities

- `toolchain-library`: image sources in recipes, the read-only image store,
  image listing in `toolchains.md`, image verification and removal.
- `container-isolation`: removes the delegated socket from the writable binds;
  replaces the delegated-client scenario and the socket-access rule with the
  engine endpoint.
- `container-launcher`: removes delegation from engine verification, launch
  contexts and image operations; adds the refusal of a leftover delegation
  opt-in.
- `container-setup`: removes the delegation choice and adds the engine image to
  installation preparation and migration of saved delegation preferences.
- `network-egress`: replaces delegation rejection with engine containment in
  the credential-free bypass evidence.
- `windows-launcher`: replaces the "unsupported on Podman machine" delegation
  refusal with the common migration refusal; the engine works in the machine.
- `container-podman-access`: retired. All its requirements are removed.

## Impact

- **Shared code**, propagated to every wrapper:
  - `launcher/core.sh`: delegation removal, engine start, endpoint, budgets and
    cleanup;
  - `network/session.py`: engine attachment for restricted sessions and
    session-owned cleanup;
  - `setup/toolchains.py`: image recipes, the store, the helper container;
  - `setup/setup.py`: the questionnaire, preferences migration and engine image
    preparation;
  - `launcher/windows/`;
  - new engine image inputs: Containerfile, configuration and a seccomp profile
    derived from the engine host's default.
- **Tests**:
  - `tests/test_launcher.py`, `tests/fake_podman.py`, `tests/test_setup.py`,
    `tests/test_runtime.py`, `tests/test_toolchains.py`,
    `tests/test_windows_bootstrap.py` and `tests/test_wrapper.py` drop
    delegation cases and gain engine and image cases;
  - `tests/run-runtime.sh` gains a path that runs from inside a session against
    the engine.
- **Documentation**: `README.md`, `AGENTS.md`, `docs/launcher-contract.md`,
  `docs/launcher-test-map.md`, `docs/network-contract.md`, `docs/setup.md` and
  `docs/validation.md`, including the spike results and the checks that stay
  machine-only.
- **Operators**: delegation users must add the images they need as toolchains.
  Sessions with images gain one extra container, a few seconds of startup and
  its budgets.
