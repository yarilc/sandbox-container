# Proposal

## Why

The Windows validation of `add-windows-installer` (rounds 8 and 9) left two
setup issues for later:

- When the Windows entry runs setup, setup prints guidance meant for a Linux
  shell. It suggests `export PATH=/home/user/.local/bin:"$PATH"` and
  `~/.bashrc`, and gives the distribution path of the managed command as the
  way to launch and to review setup. Right after that, the entry prints the
  Windows next step, so the user sees two conflicting instructions.
- Every setup tags its runtime image `localhost/<name>:setup-<release>`. A
  setup that fails or is interrupted removes its candidate release, but the
  tags it created stay. Nothing refers to them any more, and they pile up: the
  validation machine showed twelve of them.

## What Changes

- **Setup started by the Windows entry.** The shim tells setup that the
  Windows entry started it, for both `--container-setup` and the setup that
  follows `--container-install`. Setup then leaves out:
  - the shell `PATH` guidance;
  - the "Launch from a workspace" and "Review/change setup" lines with
    distribution paths.

  It states instead that the Windows entry starts sessions, and the entry
  still prints the exact next step. Setup on Linux does not change.
- **Tags of an abandoned candidate are removed.** When setup fails, is
  cancelled or is interrupted after it tagged images for its candidate
  release, it removes those `setup-<release>` tags (runtime, toolchain, proxy)
  before it exits. It removes only the names this run created: images keep
  their other tags, and the tags of retained releases, of other installation
  roots and of earlier runs stay. An image left without a name is reported,
  together with the command that removes it. Releases are still retained
  without automatic pruning, as the setup guide states.
- **Earlier leftovers.** The setup guide explains how to find `setup-*` tags
  that no `setup.json` of any installation names, and how to remove them by
  hand. Setup does not guess which tags are free: several installation roots
  share one image repository.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `container-setup`: "Repeatable setup with owned recovery" now requires
  setup to remove the image tags that an abandoned candidate created. A new
  requirement covers setup that the Windows entry starts, which leaves out the
  Linux shell and command guidance.

## Impact

- `setup/setup.py`: the guidance switch and the cleanup of the candidate's
  tags in its failure path. `setup/` is shared, so the `--setup` and
  `--setup-runtime` runner modes apply before tagging.
- `launcher/windows/core.ps1`: setup runs with the Windows marker variable.
- Tests: `tests/test_setup.py`, `tests/test_setup_wrapper.py` and
  `tests/windows/shim_tests.ps1`.
- Documentation: `docs/setup.md` for the Windows output, tag cleanup and
  manual removal of earlier tags, the README's Windows section, and
  `docs/launcher-test-map.md`.
- A short Windows check confirms the setup output from the entry.
