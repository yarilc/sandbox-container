# Propagating the shared components

`network/`, `setup/` and the shared tests listed in `tests/test_alignment.py`
are written here and copied unchanged to Claude, Codex, OpenCode, Pi and
Antigravity. `sandbox-container` is the only repository that edits them; it took
over this role from `claude-container`, and the tags `sandbox-ref-1` to
`sandbox-ref-18` keep their commits here, so adoptions continue from them.
Each wrapper pins the copy with `tests/test_reference_copy.py`, which names a
reference tag `sandbox-ref-N`, its commit and the SHA-256 of every copied file.
The durable contract is
[reference-propagation](../openspec/specs/reference-propagation/spec.md).

A wrapper never edits a shared file. A defect found in a wrapper is fixed here,
published under a new tag and propagated again.

## 1. Decide whether a new tag is needed

A change needs a new tag when it modifies, adds or removes a file under
`network/`, `setup/` or `launcher/`, or a test listed in `SHARED_TESTS`. Changes to the
wrapper, the agent profile, documentation, `tools/` or per-agent tests do not.

Before tagging, run in this repository at least every runner mode that
`tools/propagate.py` will print for the wrappers (`checklist()`), for the
shared files changed since the previous tag. Run each mode in full, without
the `-k` selections a wrapper's checklist may use, on WSL and on the native
Linux host: the wrappers validate an adoption on one host, and rely on these
runs for the rest.

| Changed shared files | Checklist entries |
| --- | --- |
| any | `unit`: `tests/test_reference_copy.py` and `tests/test_alignment.py` as host unit tests, with `SANDBOX_TEST_TMPDIR` on private storage. A wrapper whose runner offers `--shared` (the unit discovery) runs that instead. Here: the unit discovery, plus `tests/test_agent_profile.py` and `tests/test_alignment.py` |
| `setup/`, `tests/test_setup.py` | `--setup`, `--setup-runtime` |
| `network/qualif*`, `network/platform_check.py`, `network/release_acceptance.json`, `tests/test_qualification.py`, `tests/test_platform.py`, or a file listed in `SHARED_CODE` (`network/qualification_records.py`) | `--qualification` |
| guard, proxy, relay, multiplex, session, control, TLS or policy code and their tests | `--guard`, `--network` |
| `network/agent_profile.py` | `--wrapper` |
| `launcher/` outside `engine/` and `windows/` | `--wrapper` and the default runtime mode: the launcher core runs in every session |
| `launcher/engine/`, `setup/engine.py` | the engine image rebuilt from the checkout, then the engine cases: `-k SessionEngineTests` of the default runtime mode and `--network -k test_offline_session_engine_has_no_external_path`. A target without those tests runs both modes in full. A selection is dropped when its mode is already named in full |
| `launcher/windows/`, `*.ps1` | a manual step: `tools/windows-validate.ps1` on Windows PowerShell 5.1 |
| a shared `tests/test_*.py` | the mode that runs it (`test_setup` → `--setup`, `test_qualification` → `--qualification`, `test_launcher` → `--wrapper`, `test_guard` → `--guard`, `test_network_feasibility`, `test_network_policy` and `test_mux` → their modes) when the runner offers it; otherwise the module joins `unit` |
| a shared test helper (`tests/*.py` that is not a test module) | each of the target's test modules that names the helper, mapped as above; the wrapper's own `test_runtime`, `test_network_runtime`, `test_setup_runtime` and `test_wrapper` map to the default runtime mode, `--network`, `--setup-runtime` and `--wrapper` |

The checklist also names the images the entries need: the runtime image
always, and the guard toolchain for `--qualification`, `--guard` and
`--network`. `SHARED_CODE` is read from the new tag: qualification digests
those files, and the shared runtime fixtures must install them.

Record every mode and its result on each host in `docs/validation.md`, under a
section that names the new tag. A mode or a host that cannot run is recorded as
unavailable. Do not
tag while a listed mode fails. Merge into `main`, then create an annotated tag on the merge commit:

```bash
git tag -a sandbox-ref-N -m "Reference sandbox: <one-line summary>"
```

In the same merge, update this repository's own parity table in
`docs/network-contract.md`: change the `Reference (...)` cell of the
`sandbox-container` row to the new tag. Each wrapper row keeps the tag that
wrapper has adopted (`Adopted sandbox-ref-N: ...`). In a wrapper, `--apply`
moves only two cells of the "Contract adoption" column: the wrapper's own and
the reference row's. The "Real enforcement" cells name the tag each result ran
at, and keep it.

## 2. Adopt the tag in each wrapper

Run the tool from this checkout, once per wrapper, starting with a dry run:

```bash
python3 -I tools/propagate.py ../codex-container sandbox-ref-M sandbox-ref-N
```

The tool refuses to change a target when:

- its tree is not clean;
- its manifest names another tag or commit;
- a tag is missing here;
- a copied file differs from the old tag (a fork);
- the branch `adopt-sandbox-ref-N` already exists;
- its `docs/network-contract.md` has a parity table, but the tool cannot find
  the wrapper's row. It looks for one row labeled with the `display_name` of
  the wrapper's `agent/profile.json`, with the header's number of cells.

The dry run prints:

- the files to update, add and remove;
- files that changed but are outside the wrapper's adopted scope ("not adopted");
  a shared directory that the new tag introduces, such as `launcher/`, is
  adopted with the tag and listed under the added files;
- the documents and the number of references to update. For the network
  contract it also counts the old-tag mentions it keeps, for example
  `docs/network-contract.md (3, 8 kept)`;
- `review: <path>:<line>` for each line of the wrapper's own files that names
  a shared file of a directory where the tag adds or removes files;
- the reference's OpenSpec changes touched between the tags, under
  `reference changes:`;
- the commands to execute, by changed component (step 1), with the images
  they need and any manual step, and the runner line for one host
  (step 3);
- a validation-record template and a commit message.

"Not adopted" files are expected while a wrapper has adopted only part of the
shared set, for example `setup/` before its guided-setup change. They are left
alone; the wrapper's own change that adopts them copies them later.

A review line asks one question: is this line part of a hand-written list of
that directory, which the added or removed file makes stale? For example, at
`sandbox-ref-36` Claude's `tests/test_network_runtime.py` copied the engine's
build inputs from its own list, which lacked the two added files. Fix such a
list on the adoption branch, preferably by reading the shared list (here
`engine.INPUTS`); a line that only mentions a file, such as a comment, needs
nothing. Lines of the shared files, the manifest, `docs/validation.md`,
`CHANGELOG.md` and `openspec/` are never listed.

Each reference change is listed with its location in this checkout, archived
or still active, and the capabilities of its delta specs:

```text
reference changes: 2
  declare-engine-image-capabilities: archive/2026-11-26-declare-engine-image-capabilities; specs: session-container-engine
  keep-parity-history-in-propagation: archive/2026-11-26-keep-parity-history-in-propagation; specs: reference-propagation [not in target]
```

The wrapper's adoption change takes its spec deltas from these files, with the
wrapper's names. `[not in target]` means the wrapper has no main spec for the
capability: either it is reference-only, such as `reference-propagation`, and
the adoption skips it, or the adoption brings it to the wrapper, as
`session-container-engine` came with the session engine. An active change may
or may not be part of the tag; check its tasks before taking its deltas.

When the plan is right, apply it:

```bash
python3 -I tools/propagate.py ../codex-container sandbox-ref-M sandbox-ref-N --apply
```

This switches the wrapper to the new branch `adopt-sandbox-ref-N`, copies the
files byte for byte, deletes removed files, and rewrites `REFERENCE_TAG`,
`REFERENCE_COMMIT` and the manifest. When the manifest's
`SIBLING = ROOT.parent / '<name>'` names another repository (manifests written
while `claude-container` held the reference role), it also renames that
sibling, the docstring and the skip message to this checkout's directory name,
so the sibling check compares against `sandbox-container`; the dry run reports
it as `manifest: names ...`. A manifest without a `SIBLING` line is refused. It updates the tag and the full commit
only in current-state documents:

- every mention in `README.md`, `AGENTS.md`, `CONTRIBUTING.md` and
  `docs/setup.md`;
- in `docs/network-contract.md`:
  - the old tag where the reference line names it with its commit,
    `` `sandbox-ref-M` (commit `<full commit>`) ``;
  - the old commit wherever it appears;
  - in the parity table, the old tag in the "Contract adoption" cell of the
    wrapper's row and of the reference row.

  The rest of the contract keeps the old tag: the "Real enforcement" cells,
  the other wrappers' rows (which may hold the same tag), and prose that names
  it without its commit.

History stays as written: `docs/validation.md`, `CHANGELOG.md`, `todo.md` and
archived OpenSpec changes are never rewritten. The tool does not commit, merge,
tag, push or run suites.

Two files belong to the shared set but lie outside the copied directories.
When a tag introduces or changes them, copy them by hand on the same branch:

- `sandbox-container.ps1` becomes `<wrapper>-container.ps1`, byte for byte.
  The thin Windows entry has the same text in every wrapper, and
  `tests/test_alignment.py` checks it.
- `.gitattributes` is copied as is. In a clean wrapper checkout, rewrite the
  working files with LF afterwards: `git rm -r -q --cached . && git reset --hard`.
  The line-ending test in `tests/test_alignment.py` then passes.

## 3. Verify and record

Review `git diff` in the wrapper, and the `review:` lines of the plan. Commit
the adoption on its branch and push it, so that the operator's native clone can
take it.

An adoption is validated on one native host: the one where the wrapper is
used. The reference ran the modes in full on both hosts before tagging (step
1), and the copied files are byte-identical to the tag. On that host, in the
reference checkout beside the wrapper's native clone on the adoption branch,
run one line:

```bash
bash tools/adoption-run.sh ../codex-container sandbox-ref-M sandbox-ref-N
```

The runner takes the commands from `tools/propagate.py --checklist`, which
refuses a checkout that has not adopted `sandbox-ref-N`. It:

- records the commit, the kernel, Podman, the cgroup manager and controllers,
  the OCI runtime and the free space;
- stops before any command when an image the commands need is missing, or
  when less than 1 GiB is free in the home or temporary directory;
- rebuilds the wrapper's engine image from the checkout when the tag changes
  its inputs, and records its ID and its `io.containers.capabilities` label;
- runs the host unit tests with `SANDBOX_TEST_TMPDIR` on a new private
  directory: on the host's Python when it is 3.11 or later, otherwise in the
  wrapper's runtime image (the Rocky 9 lab host has Python 3.9);
- runs every entry to its own full log, also after a failure, and records the
  image tags around `--setup-runtime`;
- writes `summary.txt`: each entry's exit status and result line, then every
  skipped test with its reason. A skip that asks to prepare an image is marked
  `NOT PREPARED` and fails the run;
- packs everything into `~/sbx-logs-<wrapper>-<tag>-<host>-<time>.tar.gz`, a new
  archive for each run.

It never commits, switches branches, fetches, pushes or removes images. After a
fix on the adoption branch, rerun only the affected entries, into a new
archive:

```bash
bash tools/adoption-run.sh --only unit,network-engine ../codex-container sandbox-ref-M sandbox-ref-N
```

Fill in the validation-record template in the wrapper's `docs/validation.md`
with every entry's result, and list the checks not run, citing the reference's
record of the tag as their evidence. When the adoption also changes the
wrapper's own files, run the mode that runs them, or its cases that exercise
the change (`-k`), and record which. Manual steps, such as the Windows
validation script, are run and recorded separately.

If a suite fails because of shared code, stop: fix it here (step 1) under a new
tag and adopt that tag instead. Discard the adoption branch first:

```bash
git -C ../codex-container switch main
git -C ../codex-container branch -D adopt-sandbox-ref-N
```

A failure caused by the wrapper itself, such as a literal message that a shared
test checks, is fixed in the wrapper on the same branch.

## 4. Commit, merge and update parity

Commit in each wrapper with the printed message and the co-author trailer, then
merge `adopt-sandbox-ref-N` into `main`. The tool already moved the "Contract
adoption" cells of that wrapper's row and of the reference row. Before the
merge, update the parity table in the wrapper's `docs/network-contract.md`:
- add the adoption's results to the wrapper's "Real enforcement" cell, beside
  the earlier entries, which keep their tags;
- copy the reference row from `sandbox-container`.

Then copy the wrapper's row into `sandbox-container` and the other wrappers,
so that the reference row and the five wrapper rows are identical across the
repositories. The user pushes the branches and the tag.

## Keeping the tool in step

`tools/adoption-run.sh` reads only the tab-separated lines of
`tools/propagate.py --checklist` (`kind`, `name`, `command`); a new entry kind or
name is added to both, with `tests/test_adoption_run.py`.

`tools/propagate.py` parses the wrappers' `tests/test_reference_copy.py` as text
(`REFERENCE_TAG`, `REFERENCE_COMMIT` and one `'path': 'sha256',` line per
`MANIFEST` entry). If that file's format changes, update the tool and
`tests/test_propagate.py` in the same change.
