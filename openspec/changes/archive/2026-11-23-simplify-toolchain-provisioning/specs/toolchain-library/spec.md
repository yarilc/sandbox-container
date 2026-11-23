## MODIFIED Requirements

### Requirement: Relocatable toolchains from pinned sources
A toolchain SHALL be described by a recipe with a name, a version, one or more sources, relative `PATH` entries, environment variables, required toolchains, notes for the agent, a check command and a default flag. Each source SHALL be a subpath of an OCI image referenced by `@sha256:` digest, an HTTPS archive URL with its SHA-256, or a local archive file with its SHA-256. Sources SHALL be extracted in order into one toolchain root, each optionally limited to one subtree and placed at a relative directory of the root. An environment value SHALL be a path relative to the toolchain root or a literal. Names SHALL match `[a-z0-9][a-z0-9._-]{0,63}`. Recipes with the previous single-source schema SHALL remain valid.

#### Scenario: Image source without digest
- **WHEN** a recipe names an image by tag only
- **THEN** `add` fails without pulling or changing the library

#### Scenario: Archive checksum mismatch
- **WHEN** the SHA-256 of a downloaded or local archive differs from the recipe
- **THEN** `add` fails before extracting it, and the library is unchanged

#### Scenario: Unsafe archive content
- **WHEN** the source contains absolute paths, parent traversal, device nodes or links that resolve outside the toolchain root
- **THEN** `add` fails and the library is unchanged

#### Scenario: Literal environment value
- **WHEN** a recipe sets `GOCACHE` to the literal `/tmp/go-build` and `JAVA_HOME` to the toolchain root
- **THEN** `env.sh` exports `/tmp/go-build` and `/toolchains/<name>` respectively
- **AND** a value containing a newline or a NUL character is rejected

#### Scenario: Extracted permissions
- **WHEN** a toolchain is installed
- **THEN** its files belong to the caller, keep their executable bits, and have no setuid or setgid bit

#### Scenario: Several sources in one toolchain
- **WHEN** a recipe lists the compiler, package manager and standard library archives of one Rust release, each limited to its component subtree
- **THEN** `add` extracts them into one toolchain root and runs the check on the merged tree

#### Scenario: Two sources provide the same file
- **WHEN** two sources of one recipe would both create the same file in the toolchain root
- **THEN** `add` fails naming the file, and the library is unchanged

#### Scenario: Previous single-source recipe
- **WHEN** an operator adds a recipe written for the previous schema, with one `source` object and a local archive path
- **THEN** `add` installs it as before

### Requirement: Toolchain command on the host
`--container-toolchain` SHALL be used alone with `add <recipe-or-name>`, `list`, `remove <name>` or `verify [<name>]`. It SHALL run on the host without starting a session. `add` SHALL pull a missing digest-pinned image and download archive URLs without any maintenance setting, SHALL print each image and URL it fetches, and SHALL never build an image. Changes SHALL be serialized by a library lock and applied atomically, so that a reader sees either the previous or the new toolchain and index, never a partial one.

#### Scenario: Pull without maintenance
- **WHEN** `add` needs to pull a digest-pinned image and `SANDBOX_CONTAINER_MAINTENANCE` is unset
- **THEN** the command pulls the image, names it in its output, and installs the toolchain

#### Scenario: Fetch failure
- **WHEN** a pull or a download fails
- **THEN** `add` fails naming the image or URL, and the library is unchanged

#### Scenario: Concurrent changes
- **WHEN** two `--container-toolchain` commands change the library at the same time
- **THEN** they run one after the other and the index lists the result of both

#### Scenario: Replace and remove
- **WHEN** `add` installs a name that already exists, or `remove` deletes one
- **THEN** the old directory is replaced or removed only after the new state is complete, and the index is regenerated

#### Scenario: Required toolchains
- **WHEN** a recipe requires a toolchain that is not installed, or `remove` targets a toolchain that another one requires
- **THEN** the command fails naming the missing or dependent toolchain, and the library is unchanged

## ADDED Requirements

### Requirement: Archive downloads by the toolchain command
`add` SHALL download an archive source named by URL itself, only over HTTPS with certificate verification, following redirects only to HTTPS URLs. It SHALL trust the host CA bundle saved by setup when host CA trust is enabled, and the system trust otherwise. It SHALL verify the SHA-256 before extracting anything and SHALL keep no downloaded file after the command ends.

#### Scenario: Catalog recipe with archive URLs
- **WHEN** the operator adds a recipe whose sources are HTTPS archive URLs, without any local file or environment variable
- **THEN** `add` downloads and verifies the archives, installs the toolchain, and leaves no downloaded file behind

#### Scenario: Plain HTTP URL
- **WHEN** a recipe names an `http://` archive URL
- **THEN** `add` fails before any download, and the library is unchanged

#### Scenario: Redirect to plain HTTP
- **WHEN** the HTTPS server redirects the download to an `http://` URL
- **THEN** `add` fails without following it, and the library is unchanged

#### Scenario: Network that re-signs TLS
- **WHEN** setup saved a host CA bundle and the network re-signs TLS with that CA
- **THEN** the download verifies the server certificate against that bundle and succeeds

### Requirement: Release catalog of reviewed recipes
The protected release SHALL contain a catalog of reviewed recipes, shared by every wrapper. `add <name>`, with an argument that contains no `/` and does not end in `.json`, SHALL install the catalog recipe of that name; any other argument SHALL be read as a recipe file. Catalog recipes SHALL use only digest-pinned images and HTTPS archive URLs with SHA-256. `list` SHALL show the catalog recipes that are not installed.

#### Scenario: Toolchain by name
- **WHEN** the operator runs `--container-toolchain add java21`
- **THEN** the release's `java21` recipe is installed, with no recipe file and no environment variable

#### Scenario: Unknown name
- **WHEN** the operator runs `--container-toolchain add jav21`
- **THEN** the command fails naming the available catalog recipes, without fetching anything

#### Scenario: Installed copy without the checkout
- **WHEN** the Windows checkout was deleted after `--container-install` and the operator runs `sandbox-container --container-toolchain add go`
- **THEN** the catalog recipe from the installation in the machine is installed

#### Scenario: Available recipes listed
- **WHEN** the operator runs `--container-toolchain list` with only `java21` installed
- **THEN** the output lists `java21` as installed and the other catalog recipes as available

### Requirement: Operator recipes outside writable mounts
`add` SHALL refuse a recipe file inside a writable mount that a session started from the current directory would have: the workspace, widened to its parent by the saved worktree scope, and the state directories. The refusal SHALL name the recipe and happen before any fetch. Catalog recipes and local archive files SHALL NOT be subject to this check, because the release protects the former and the recipe pins the latter.

#### Scenario: Recipe written in the workspace
- **WHEN** the operator runs `--container-toolchain add tools/java.json` from a project directory that contains that file
- **THEN** `add` fails naming the recipe as inside the workspace, fetches nothing, and the library is unchanged

#### Scenario: Recipe kept by the operator
- **WHEN** the recipe is in `~/recipes` and the operator runs `add ~/recipes/java.json` from a project directory
- **THEN** `add` proceeds

#### Scenario: Saved worktree scope
- **WHEN** setup saved the worktree scope and the recipe is in a sibling of the current project
- **THEN** `add` refuses it, because sessions started from the project mount the parent

#### Scenario: Local archive in the workspace
- **WHEN** a recipe kept outside the workspace names a local archive inside it
- **THEN** `add` accepts the archive if its SHA-256 matches the recipe

### Requirement: Windows drive paths from the Windows entry
When the toolchain command runs from the Windows entry, `add` SHALL translate a recipe path or a local archive path written as a Windows drive path to its drive mount in the machine distribution. It SHALL refuse UNC paths, paths inside a WSL distribution and drives the distribution does not mount, before any fetch.

#### Scenario: Recipe path from PowerShell
- **WHEN** the operator runs `sandbox-container --container-toolchain add C:\Work\recipes\java.json` from PowerShell
- **THEN** `add` reads `/mnt/c/Work/recipes/java.json` in the machine

#### Scenario: Windows archive path in a recipe
- **WHEN** a recipe added from the Windows entry names the local archive `C:\Downloads\node.tar.xz`
- **THEN** `add` reads `/mnt/c/Downloads/node.tar.xz`

#### Scenario: Network share
- **WHEN** the recipe path is `\\server\share\java.json`
- **THEN** `add` fails naming network paths as unsupported, and the library is unchanged

### Requirement: Windows library location is documented
Documentation SHALL state that on Windows the toolchain library lives inside the Podman machine's distribution, is shared by the wrappers that run in that machine, and is lost when the machine is recreated, after which the operator adds the toolchains again.

#### Scenario: Operator reads the Windows documentation
- **WHEN** an operator reads the README Windows section
- **THEN** it states where the library lives and that recreating the machine removes it
