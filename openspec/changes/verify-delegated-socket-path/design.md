# Design

## Context

`core_engine_delegation` in `launcher/core.sh` selects the delegation socket, checks that the caller can read and write it, queries the service with `{{.Host.Security.Rootless}} {{.Host.RemoteSocket.Path}}`, strips a `unix://` prefix and requires `rootless == true` and an absolute path without LF. The reported path then becomes the bind source `--volume "<path>:/run/podman/podman.sock:rw"`. The reported path must be trusted in one case: a wrapper that itself runs in a container reaches the host service through a remapped socket, and the host path it must bind is not visible in its namespace (`test_socket_precedence_and_remapping`, `test_containerized_caller_with_remapped_socket` in the wrapper runtime suites).

`setup/setup.py` `verify_socket` applies the same rootless and absolute-path rule when guided setup checks an endpoint. `network/qualification_records.py` reads the engine's own socket path only as part of the qualification identity; it is never mounted and stays unchanged.

Antigravity's old launcher refused a reported path made only of slashes; the core accepts it and, with the fake engine, binds `/:/run/podman/podman.sock:rw`. The user classified that as a visible change during the Antigravity adoption, then chose this fix (option 2) on 2026-11-17.

## Goals / Non-Goals

**Goals:**
- A reported host socket path never makes the launcher mount the host root or another existing non-socket into a session.
- Callers inside a container keep working with remapped sockets.
- Setup and the launcher accept and refuse the same answers.

**Non-Goals:**
- Proving that a path the caller cannot see is a socket on the host. The service's answer stays trusted there, as today; with delegation enabled the session already controls that service and can request host mounts through its API.
- Changing the qualification identity record or the socket selection order.

## Decisions

1. **Two checks after the existing ones, in `core_engine_delegation`.**
   - A path matching `^/+$` (after removing `unix://`) is refused: `Podman socket <socket> reported the root directory as its host socket path`.
   - When `[[ -e "$host_socket" || -L "$host_socket" ]]` holds, `[[ -S "$host_socket" ]]` must hold too; otherwise `Podman socket <socket> reported a host socket path that is not a socket here: <path>`. `-S` follows symbolic links, so a link to the socket passes, and a dangling link (`-L` without `-e`) is refused.

   Both run before image operations, as the existing checks do, and also in the build-only operation, which verifies delegation settings (U16).

   Alternatives rejected:
   - *Requiring the path to exist:* breaks every containerized caller with a remapped socket.
   - *Detecting a container through `/run/.containerenv` or cgroup paths:* unreliable across engines and still unable to see the host path; the existence test is the actual question.
   - *Comparing the reported path with the client-visible socket:* a host caller may legitimately reach the same socket through a symlink or another path; the `-S` test covers that case without false refusals.

2. **Setup mirrors the rule.** `verify_socket` refuses a slash-only path and, when `os.path.lexists(host_path)`, requires `Path(host_path).is_socket()`. The error stays the existing setup message, extended with "a usable host socket path".

3. **Tests.**
   - `tests/test_launcher.py`: a new shared case, `test_reported_host_socket_must_be_a_socket_when_visible`, reports through `FAKE_HOST_SOCKET`: `/`, `//`, `unix:///` (refused); a directory and a regular file in the test base and a dangling symlink (refused); the test's own bound socket (accepted, mounted); `/host/podman.sock`, absent (accepted, mounted). Each refusal asserts the endpoint in stderr and no `image`, `build` or `create` call, with and without `--container-build`.
   - `tests/test_setup.py`: `test_socket_validation_rejects_rootful_and_cr_responses` gains `true /`, `true unix:///`, an existing directory and an existing regular file; the absent `/host/socket` stays accepted.

4. **Documentation and tag.** `docs/launcher-contract.md` adds the rule to the phase 3-4 delegation row and the core rules, naming the remapped limit; `docs/launcher-test-map.md` maps Antigravity's `test_complete_socket_response_required` to the new shared case; `docs/validation.md` records the run. The merge is tagged `sandbox-ref-25` after the operator's setup on the three hosts, as for `sandbox-ref-24`.

5. **Validation scope.** The core and setup change, so: the extended cases against the current core (expected to fail), then after the fix `tests.test_launcher`, `tests.test_wrapper`, `tests.test_alignment` and `tests.test_setup`; the unit discovery; `bash tests/run-runtime.sh --wrapper`, `--setup` and the default runtime run (its real delegated child-container and remapped-socket cases exercise both branches against a real service); `git diff --check`.

## Risks / Trade-offs

- **[A containerized caller still trusts an invisible path]** → Documented limit; the slash-only refusal still applies there, and delegation already grants equivalent authority through the API.
- **[A host-side path visible in a container by coincidence is refused]** → Fails closed with a path-specific message; the caller can choose a socket override that matches.
- **[Installed qualification reports no longer match]** → The operator reruns `--container-setup` on the three hosts before the tag.
