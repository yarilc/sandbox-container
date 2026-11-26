## MODIFIED Requirements

### Requirement: Current-state references only
An applied run SHALL replace the old tag and commit with the new ones only in current-state documents:
- every mention in the README, `AGENTS.md`, `CONTRIBUTING.md` and `docs/setup.md`;
- the current references of `docs/network-contract.md`, as "Network contract references" defines them.

It SHALL NOT change `docs/validation.md`, `CHANGELOG.md`, `todo.md` or archived OpenSpec changes, which record history.

#### Scenario: Historical record keeps the old tag
- **WHEN** the target's validation record and changelog mention the old tag
- **THEN** those files are unchanged after the applied run, while the README and the network contract name the new tag

### Requirement: Parity table names the reference
The parity table in `docs/network-contract.md` SHALL have a row for `sandbox-container` and one row for each wrapper, Claude included, identical in every repository. Its contract adoption cell SHALL read `Reference (sandbox-ref-N, ...)` with the latest tag in the reference row, and `Adopted sandbox-ref-N: ...` with the adopted tag in each wrapper row. The real enforcement cells SHALL name the tag each result ran at, and keep it when a later tag is adopted.

#### Scenario: Tag created
- **WHEN** `sandbox-ref-19` is created
- **THEN** the reference row names it, and each wrapper row names the tag that wrapper has adopted

#### Scenario: Results from an earlier tag
- **WHEN** a wrapper adopts a new tag, and its real enforcement cell records results from the previous tag
- **THEN** those results still name the previous tag, and results of the new tag are added beside them

## ADDED Requirements

### Requirement: Network contract references
In `docs/network-contract.md`, an applied run SHALL replace only:
- the old tag where the reference line names it with the old commit;
- the old commit wherever it appears;
- the old tag in the parity table's contract adoption cell of the target's own row and of the reference row.

The target's own row SHALL be the row labeled with the `display_name` of the target's `agent/profile.json`. The dry run SHALL report the references it will replace and the old-tag mentions it keeps.

#### Scenario: Parity history keeps the old tag
- **WHEN** a real enforcement cell of the target's parity table records a result as `sandbox-ref-34 modes passed`, and the target adopts `sandbox-ref-35` from `sandbox-ref-34`
- **THEN** that cell still names `sandbox-ref-34` after the applied run, while the target's and the reference's contract adoption cells name `sandbox-ref-35`

#### Scenario: Other wrappers keep their adoption
- **WHEN** Codex adopts `sandbox-ref-35` from `sandbox-ref-28`, and the Antigravity row of its parity table reads `Adopted sandbox-ref-28`
- **THEN** the Antigravity row is unchanged after the applied run, and only the Codex row's contract adoption cell names `sandbox-ref-35`

#### Scenario: Reference line
- **WHEN** the target's network contract says that the shared components come from `sandbox-container` at the old tag, with its commit
- **THEN** after the applied run that line names the new tag and the new commit

#### Scenario: Dry run counts kept mentions
- **WHEN** the tool runs without `--apply` against a target whose network contract mentions the old tag in history entries
- **THEN** the documents line reports the references to replace and the mentions kept in the network contract, and the target is unchanged

### Requirement: Unreadable parity table is refused
When the target's network contract has a parity table, the tool SHALL refuse the target before writing anything if:
- its profile has no `display_name`;
- the table has no single row with that label;
- a row lacks the header's cells.

The refusal SHALL name the problem.

#### Scenario: Target without a parity row
- **WHEN** the target's network contract has a parity table without a row for its profile's `display_name`
- **THEN** the tool exits nonzero naming the missing row, and writes nothing

#### Scenario: Row with an extra cell
- **WHEN** a row of the target's parity table has more cells than the header
- **THEN** the tool exits nonzero naming the line, and writes nothing
