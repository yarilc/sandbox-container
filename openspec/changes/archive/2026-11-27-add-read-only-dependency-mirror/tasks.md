# Tasks

Run checks in the Windows Podman Machine working session. For tests that
execute stubs, set `SANDBOX_TEST_TMPDIR` to disposable executable storage on
the workspace mount. Tests that exercise protected paths need private native
storage, as provided by `tests/run-runtime.sh` when its images and engine
prerequisites are available. Record environmental limitations and their reasons
in `docs/validation.md` and move those checks to the follow-up after closure.

## 1. Operator profiles and launch selection

- [x] 1.1 Implement the strict profile parser, private shared library and
  `--container-mirror add`, `list` and `remove` dispatch. Add `verify` with
  the trusted connection and index probe in task 2.2. Document profile fields,
  management commands and protected catalog paths. Run
  `python3 -m unittest discover -s tests -p test_mirror_profiles.py -v` for
  catalog and file import, atomic replacement, malformed input and writable
  workspace, widened worktree, state and aliased paths.
- [x] 1.2 Resolve and snapshot profile defaults and `.sandbox-mirrors.json`
  selections at launch. Document format and precedence. Extend `test_launcher.py`
  to exercise sorted defaults, duplicate and unknown names, malformed selection,
  concurrent library edits, startup revisions and the offline default.
- [x] 1.3 Accept optional `registries` in schema 2 recipes and the current
  read-only index, and consume names only from eligible default toolchains.
  Update the toolchain guide. Run `test_toolchains.py` and `test_launcher.py`
  for legacy and image-only recipes, invalid names, expired base verification,
  disabled toolchains and unchanged offline checks.

## 2. Trusted mirror and transport

- [x] 2.1 Implement the trusted request parser, typed route authorization,
  upstream header filtering and bounded HTTP responses. Run
  `python3 -m unittest discover -s tests -p test_dependency_mirror.py -v`
  for valid reads, denied methods, request bodies, ambiguous paths and
  framing, missing profiles and credential stripping with upstream evidence.
- [x] 2.2 Implement verified HTTPS, scoped trusted address resolution,
  redirects and per-upstream `--container-mirror verify`. Extend the mirror
  and profile suites with controlled trusted and untrusted TLS, public and
  LAN address checks, out-of-scope responses, per-upstream verification
  diagnostics and positive index probes.
- [x] 2.3 Implement bounded cache storage and streaming. Use the mirror suite
  to verify atomic successful entries, revalidation, concurrent cancellation,
  revision partitioning, cache limits and deletion of partial artifacts.
- [x] 2.4 Extend mux, relay and trusted proxy dispatch with the second stream
  type and one versioned identity. Run `python3 -m unittest discover -s tests
  -p test_mux.py -v` and `test_tls_proxy.py` for mixed-stream progress under
  load, reserved provider capacity, framing failures and channel shutdown.

## 3. Protected setup and qualification

- [x] 3.1 Wire explicit `mirror` mode into the guard, shared launcher, session
  helper, protected setup, image build and Windows shim. Cover installed
  artifact identities, incompatible versions, preparation failure, rollback,
  managed command forwarding and the empty-mode fallback with `test_setup.py`,
  `test_launcher.py` and the Windows shim tests available through
  `tools/powershell.sh`. Update setup and network documentation, including
  the mirror request visibility notice and existing provider disclosures.
- [x] 3.2 Add credential-free qualification controls for mirror traffic through
  the installed guard and relay. Extend `test_qualification.py` and
  `test_network_runtime.py` to prove the positive read, upstream absence for
  denied writes and paths, credential stripping, mode separation, closed
  behavior on peer loss and invalidation of reports issued under an older
  protocol. Run the component suites and `tests/run-runtime.sh --qualification`
  in the session where supported.

## 4. RPM and nested systemd targets

- [x] 4.1 Implement the RPM route adapter and document the DNF `baseurl`
  configuration for a single selected repository, local signing keys and
  signature checks. Support explicitly approved split package prefixes and
  the Amazon Linux 2023 CDN path hierarchy. Use fixture cases in
  `test_dependency_mirror.py` for `repomd.xml`, secondary indexes, signatures,
  relative package links, RPM bytes and excluded paths.
- [x] 4.2 Add the protected Rocky Linux 9 and Amazon Linux 2023 public
  profiles. Record distro, repository and architecture combinations and the
  catalog procedure for resolving a release-specific AL2023 `mirror.list`
  into a reviewed base URL. Verify catalog revisions and URLs in
  `test_mirror_profiles.py` and exercise `--container-mirror verify` against
  the actual repositories when reachable from the working session.
- [x] 4.3 Add credential-free RPM repository and build fixtures. Extend
  `test_network_runtime.py` to check a nested DNF refresh and a build `RUN`
  with `--network=host`, expected denial with `--network=none`, and package
  installation and signature verification through the mirror when a signed
  fixture is available. Use the registered Rocky Linux 9 and AL2023 systemd
  targets and prove the package was absent before install. Assert the package
  identity, test the installed service and journal, and clean up containers,
  images and repository state. Document the nested commands with their
  namespace and target prerequisites.
- [x] 4.4 Add a Molecule scenario for the two targets and the same mirror
  repository contract, with explicit client configuration and idempotent
  service assertions. Verify the scenario and run `molecule test` when the
  controller is available in the working session. Record any unavailable
  orchestration separately from the direct DNF and systemd results.

## 5. Language package clients

- [x] 5.1 Add Maven read routes and the generated mirror settings. Document
  using them with the reviewed Maven toolchain. In `test_dependency_mirror.py`
  assert permitted artifact, plugin and checksum requests. With Maven
  available, run a small build against the controlled fixture.
- [x] 5.2 Add PyPI simple index routes and approved file URL rewriting.
  Document the generated `PIP_INDEX_URL`. Verify HTML and JSON results,
  hash preservation and denied origins in the mirror suite, and install a
  fixture distribution with pip when available.
- [x] 5.3 Add npm read routes, tarball URL rewriting and generated registry
  settings. Document lockfile and audit behavior. Verify scoped metadata,
  denied registry writes, tarball integrity and an `npm install` against the
  controlled fixture with a fresh cache.
- [x] 5.4 Add Cargo sparse index and crate routes with generated source
  replacement. Document selecting those settings. Verify normalization,
  approved download locations and checksum bytes in the mirror suite and
  run `cargo fetch` against a fixture when Cargo is available.
- [x] 5.5 Add Go module and checksum routes and generated `GOPROXY` settings.
  Document the operator module-prefix policy and preserved checksum checking.
  Verify normalized prefix and checksum lookup enforcement with an upstream
  positive control in the mirror suite. Run `go mod download` for an allowed
  module with checksum verification when Go is available.

## 6. Integration in the working session

- [x] 6.1 Run the mirror, mux, qualification, launcher, toolchain and engine
  regressions, `tests/test_alignment.py`, and the applicable shared runtime
  modes with their available fixtures. Verify protected release and propagation
  inventories include the newly shared files. Check `git diff --check` and
  `openspec validate add-read-only-dependency-mirror --strict`.
- [x] 6.2 Record the setup path, fixture controls, RPM build and systemd
  results, language client results, and any unavailable checks with reasons
  and versions in `docs/validation.md`. Before closing, verify the record
  distinguishes component checks, traffic through the installed boundary,
  and checks against real upstreams.

## Follow-up after closure

- Repeat the applicable runtime and qualification modes on native Linux and
  any other supported WSL or Windows PowerShell environment. Verify native
  Podman Machine setup and approved production repositories when available.
- Run checks unavailable in the working session and record their results,
  including the full Molecule scenario if its controller was unavailable.
- Tag the reference and propagate shared changes through the normal adoption
  workflow. Track defects found on other environments in new changes.
