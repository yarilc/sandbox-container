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
`network/` or `setup/`, or a test listed in `SHARED_TESTS`. Changes to the
wrapper, the agent profile, documentation, `tools/` or per-agent tests do not.

Before tagging, run in this repository at least every runner mode that
`tools/propagate.py` will print for the wrappers (`checklist()`), for the
shared files changed since the previous tag:

| Changed shared files | Modes |
| --- | --- |
| any | `--shared` (here: the unit discovery), plus `tests/test_agent_profile.py` and `tests/test_alignment.py` |
| `setup/`, `tests/test_setup.py` | `--setup`, `--setup-runtime` |
| `network/qualif*`, `network/platform_check.py`, `network/release_acceptance.json`, `tests/test_qualification.py`, `tests/test_platform.py` | `--qualification` |
| guard, proxy, relay, multiplex, session, control, TLS or policy code and their tests | `--guard`, `--network` |
| `network/agent_profile.py` | `--wrapper` |

Also run `--qualification` whenever a changed file is listed in
`SHARED_CODE` (`network/qualification_records.py`), such as a new setup
module. Qualification digests those files, and the shared runtime fixtures
must install them.

Record every mode and its result in `docs/validation.md`, under a section that
names the new tag. A mode that cannot run is recorded as unavailable. Do not
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
- the runner modes to execute;
- a validation-record template and a commit message.

"Not adopted" files are expected while a wrapper has adopted only part of the
shared set, for example `setup/` before its guided-setup change. They are left
alone; the wrapper's own change that adopts them copies them later.

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

Review `git diff` in the wrapper. Run every runner mode the tool listed, in the
wrapper checkout, plus any other mode the change can affect. Fill in the
validation-record template in the wrapper's `docs/validation.md` with the
results.

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

`tools/propagate.py` parses the wrappers' `tests/test_reference_copy.py` as text
(`REFERENCE_TAG`, `REFERENCE_COMMIT` and one `'path': 'sha256',` line per
`MANIFEST` entry). If that file's format changes, update the tool and
`tests/test_propagate.py` in the same change.
