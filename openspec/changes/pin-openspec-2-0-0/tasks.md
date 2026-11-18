## 1. Baseline

- [x] 1.1 Record the pre-change state: the current runtime image ID and its `openspec --version` (1.16.0). Seed a disposable state directory by running the 1.16.0 image's OpenSpec once against a temporary project, so that `~/.config/openspec` holds 1.16.0 state.
- [x] 1.2 Run `python3 -m unittest discover -s tests -p test_image_pins.py` on the unchanged tree and record the result.

## 2. Pin

- [x] 2.1 Set `ARG OPENSPEC_VERSION=2.0.0` in `Containerfile`. Leave the base digest and every other input unchanged.
- [x] 2.2 Update the version-range mutation in `tests/test_image_pins.py` (`^1.16.0`) to the new pin. The pin tests pass, and every mutated recipe is still rejected.
- [x] 2.3 Confirm that no other tracked file outside `docs/validation.md` and the archive names `1.16.0` as the current pin (`git grep -n 1.16.0`).

## 3. Build and verify

- [x] 3.1 Rebuild the runtime image under maintenance authorization (`SANDBOX_CONTAINER_NETWORK=unrestricted SANDBOX_CONTAINER_MAINTENANCE=1 ./sandbox-container.sh --container-build`). The image must report `openspec --version` `2.0.0`, and the build must keep the HTTPS Debian sources.
- [x] 3.2 Run `tests/image-smoke.sh` through the wrapper's shell mode. It must pass and print `2.0.0`.
- [x] 3.3 Offline round trip inside the image, on a temporary project, with the state seeded in 1.1: initialize without agent tools, then `openspec new change`, `openspec validate --all` and `openspec list --json`. Every command must succeed. Record any network attempt the guard reports and any change to `~/.config/openspec`.
- [x] 3.4 Run the full credential-free suite (unit, shared, setup, runtime, network, guard), as in previous maintenance entries. Every group passes.
- [x] 3.5 Run `bash tools/shellcheck.sh .` and `git diff --check`. Both must be clean.

## 4. Record

- [x] 4.1 Add a dated section to `docs/validation.md`. It records:
  - the change name and the version rule (newest non-prerelease at least 72 hours old on 2026-11-18);
  - the old and new image IDs and `openspec --version`;
  - the round-trip and state results, and the suite results;
  - the unchanged base digest.
- [x] 4.2 Update the image summary in the reference-shell section of `docs/validation.md` to `@fission-ai/openspec@2.0.0`.
- [x] 4.3 Run `openspec validate pin-openspec-2-0-0 --strict` with the operator's planning CLI.
- [x] 4.4 Commit on `main`, without a tag.

## Workflow follow-up

- The operator pushes `main` and reruns `--container-setup` on the three hosts.
- Archive with `/opsx:archive pin-openspec-2-0-0`. There are no specs to sync.
- Next changes: Antigravity (OpenSpec only), then OpenCode, Claude, Codex and Pi, each in its own repository.
