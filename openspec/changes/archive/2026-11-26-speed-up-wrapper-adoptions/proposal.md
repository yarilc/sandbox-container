# Proposal

## Why

Wrapper adoptions take hours, mostly in round trips between the operator and
the maintainer:
- the operator receives a block of commands per host, pastes it, and copies an
  archive back;
- a command left out, or a file not written, costs another round;
- the checklist does not name every component a tag touches, so the selection
  of tests is done by hand each time.

Claude's adoption of `sandbox-ref-36` (2026-11-26) took one host and one line.
The perimeter was the changed components. Three manual steps showed what the
tool should do itself:
- **Missing modes:** `--wrapper` and the engine cases were missing from the
  checklist, because it maps no `launcher/` change to a mode.
- **Hand-written list:** Claude's own network test kept a list of the engine's
  build inputs without the two files the tag added. Only a dry run of the
  network fixture would have shown it.
- **Temporary storage:** the host unit tests failed because the line set no
  private temporary storage.

Codex, Antigravity, OpenCode and Pi still have to adopt `sandbox-ref-36` from
`sandbox-ref-28`. This change makes each of those adoptions one run per host.

## What Changes

- **Checklist by component.** For each file that changed between the tags,
  `tools/propagate.py` names the commands that exercise it, ready to run:
  - **`launcher/core.sh`:** `--wrapper` and the default runtime mode;
  - **`launcher/engine/` and `setup/engine.py`:** the engine cases of the
    default and network runtime modes, selected with `-k` when the target
    has them. Otherwise the whole modes run;
  - **a qualified file:** a file listed in `SHARED_CODE` adds
    `--qualification`, as the tagging rule already requires;
  - **a changed shared test module:** its runner mode, or, without one, the
    host unit tests with private temporary storage;
  - **a changed shared test helper:** the test modules that name it;
  - **Windows files:** a manual step on Windows.

  The existing mappings for `setup/`, qualification, guard and network code
  stay.
- **Review warnings in the plan.** When a tag adds or removes a shared file,
  the dry run lists the target's own files that name a shared file of the
  same directory, with file and line. The applied run lists them too.
  Such a file may hold a hand-written list of that directory. The warnings do
  not block the run.
- **Reference changes of the range.** The plan lists the reference's OpenSpec
  changes touched between the tags:
  - each with its current location, archived or active;
  - its delta specs;
  - the capabilities the target does not have.

  The adoption change can take its spec deltas from them.
- **New: `tools/adoption-run.sh`,** reference-only and run on the operator's
  host from the reference checkout. It takes the wrapper checkout and the two
  tags, and runs what `tools/propagate.py --checklist` prints for a wrapper
  that has adopted the new tag:
  - **Preflight:** the commit, versions and free space, and the images the
    selected commands need.
  - **Engine image:** rebuilt from the checkout when the tag changes its
    inputs, with its capability label recorded.
  - **Unit tests:** host unit tests on the host's Python when it is 3.11 or
    later, with private temporary storage. Otherwise they run in the agent's
    runtime image.
  - **Logs:** every command writes a full log, even after an earlier failure,
    and a summary records each exit status, the result line and every skip
    reason.
  - **Archive:** one archive in the home directory, under a name that names
    the wrapper, the tag, the time and the host.
  - **Rerun:** `--only` reruns chosen entries into a new log directory.

  It never commits, switches branches, pushes or removes images.
- **Procedure.** `docs/propagation.md` gives the adoption a validation
  perimeter: the runner's commands on one host. The full matrix on both
  native hosts stays the reference's job before each tag, and the procedure
  says so. A wrapper reruns a mode outside the perimeter when its own code
  for that mode changes.

## Capabilities

### New Capabilities

- `adoption-runner`: the reference-only runner. It covers preflight, the
  engine image preparation, logs and archive, the summary, and reruns.

### Modified Capabilities

- `reference-propagation`:
  - the verification checklist selects commands by changed component, with
    `-k` engine cases, host unit modules and the qualification rule;
  - the plan warns about the target's files that name shared files of a
    directory with additions or removals;
  - the plan lists the reference changes of the range;
  - the reference's runs before tagging cover both native hosts;
  - the procedure states the one-host adoption perimeter.

## Impact

- **Reference files:**
  - `tools/propagate.py`, with a new `--checklist` output;
  - the new `tools/adoption-run.sh`;
  - `tests/test_propagate.py` and a new `tests/test_adoption_run.py`;
  - `docs/propagation.md`.

  `tools/` is reference-only, so no new `sandbox-ref-N` tag is needed and no
  wrapper copies anything.
- **Wrappers:** unchanged. Their next adoption uses the new output and the
  runner.
- **Operators:**
  - one line per host, run from the reference checkout:
    `bash tools/adoption-run.sh ../<wrapper> <old> <new>`;
  - one archive to copy back.
- **Hosts:** the runner and `tools/propagate.py` must run on the Rocky 9 lab
  host's Python 3.9, as well as on WSL.
