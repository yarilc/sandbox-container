# Proposal

## Why

With Podman delegation enabled, the launcher mounts the host socket path that the selected service reports, `{{.Host.RemoteSocket.Path}}`, at `/run/podman/podman.sock`. It only checks that the path is absolute. A service that reports `/` (or `unix:///`) makes the launcher bind the host root read/write into the session; any other absolute directory, such as the caller's home, is mounted the same way. A legitimate rootless Podman always reports its real socket, so this needs a misbehaving or fake service on the selected endpoint, but the launcher should not turn such an answer into a host mount. Antigravity's adoption of the core found the gap: its old launcher refused a path made only of slashes.

## What Changes

- The launcher refuses a reported host socket path made only of slash characters, also after removing a `unix://` prefix.
- When the reported path exists in the caller's own filesystem namespace, the launcher requires it to be a Unix socket. A path that exists there but is a directory, a regular file or another non-socket stops startup before image operations.
- A reported path that does not exist in the caller's namespace is still accepted. This is the remapped case of a wrapper that runs inside a container and reaches the host service through another path; the service's answer stays trusted there, and the documentation states that limit.
- Guided setup applies the same rule when it verifies the selected endpoint.
- The shared launcher tests and the shared setup tests cover the slash-only paths, an existing directory, an existing regular file, an existing socket and the remapped path.
- `docs/launcher-contract.md`, `docs/launcher-test-map.md` and `docs/validation.md` record the rule; the result is tagged `sandbox-ref-25`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `container-podman-access`: "Exposed Podman service must report rootless operation" refuses a slash-only host socket path and an existing non-socket path, and names the remapped limit.

## Impact

- **Code:** `launcher/core.sh` (`core_engine_delegation`) and `setup/setup.py` (`verify_socket`); `tests/test_launcher.py` and `tests/test_setup.py`.
- **Wrappers:** a new tag, `sandbox-ref-25`. Claude, Codex and Antigravity adopt it in small changes that copy the core, setup and the two test files; Pi and OpenCode adopt it in their full adoptions. Antigravity's validation record notes that the old case `test_complete_socket_response_required` (`true /`), classified as a visible change, is now covered by a shared case.
- **Qualification:** the installed core and setup change, so installations rerun `--container-setup`.
- **Behavior:** a delegated launch whose service reports an existing non-socket path, or a slash-only path, now stops; legitimate services are unaffected.
