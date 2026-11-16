# Spec Delta

## MODIFIED Requirements

### Requirement: Exact propagation within the adopted scope
The tool SHALL compute the shared files (as listed by the new tag's `tests/test_alignment.py`) modified, added or removed between the tags, limited to the target's adopted scope: its manifest files, additions under a directory it already adopts, and every file of a shared directory that the new tag introduces. A dry run SHALL only print the plan. An applied run SHALL write each file from the new tag byte for byte, delete removed files, and rewrite `REFERENCE_TAG`, `REFERENCE_COMMIT` and the manifest hashes.

#### Scenario: Dry run
- **WHEN** the tool runs without `--apply`
- **THEN** it prints the files to update, add and remove and the documents to touch, and the target is unchanged

#### Scenario: Applied adoption
- **WHEN** the tool runs with `--apply` on a valid target
- **THEN** it creates the branch `adopt-<new tag>`, the target's shared files equal the new tag, and the target's `tests/test_reference_copy.py` passes

#### Scenario: Partially adopted target
- **WHEN** a target has adopted `network/` but not yet `setup/common.py` and the new tag changes `setup/common.py`
- **THEN** the tool leaves `setup/common.py` absent and reports it as outside the adopted scope

#### Scenario: New shared directory
- **WHEN** the new tag adds the shared directory `launcher/` and the shared tests `tests/test_launcher.py` and `tests/fake_podman.py`
- **THEN** a target that adopts the old tag's shared tests receives all of them as additions
