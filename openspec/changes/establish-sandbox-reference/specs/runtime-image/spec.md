# Spec Delta

## MODIFIED Requirements

### Requirement: Runtime image inputs are pinned
The image recipe SHALL install the exact version of `@fission-ai/openspec` recorded in the repository and no agent CLI. It SHALL reference the base image by registry digest, using the same pinned base as the agent wrappers. No floating tag, `latest` specifier or version range SHALL select an image input.

#### Scenario: Build uses recorded versions
- **WHEN** the image is built under explicit maintenance authorization
- **THEN** `openspec --version` in the resulting image reports exactly the recorded version
- **AND** the base layer comes from the recorded digest

#### Scenario: Unpinned input is rejected by tests
- **WHEN** the recipe names a package without an exact version, uses `@latest`, or references the base image without a digest
- **THEN** the credential-free unit suite fails

### Requirement: Image package sources use verified HTTPS
The runtime image recipe SHALL fetch Debian packages only from `https://` sources, with TLS peer verification enabled for every fetch. The build SHALL NOT require outbound port 80 and SHALL NOT fall back to plain HTTP. The built image SHALL keep HTTPS Debian sources.

#### Scenario: Host blocks outbound port 80
- **WHEN** the runtime image is built under maintenance authorization on a host where outbound TCP 80 is blocked and HTTPS to the Debian, npm and container registries is reachable
- **THEN** the build completes and the image reports the recorded OpenSpec version

#### Scenario: Built image keeps HTTPS sources
- **WHEN** a user inspects the Debian source configuration inside a container started from the runtime image
- **THEN** every Debian source URI uses `https://`

#### Scenario: Insecure transport is rejected by tests
- **WHEN** the recipe uses a plain-HTTP Debian source or disables apt TLS peer or host verification
- **THEN** the credential-free unit suite fails and names the violation

## ADDED Requirements

### Requirement: Pinned input updates follow explicit maintenance
Documentation SHALL describe the update procedure:
- change the recorded versions or base digest;
- rebuild with exact `SANDBOX_CONTAINER_MAINTENANCE=1`;
- rerun setup or qualification;
- record the outcome in the validation record.

Runtime sessions SHALL NOT update the pinned inputs.

#### Scenario: Maintainer updates a pinned input
- **WHEN** a maintainer follows the documented procedure to move to a new OpenSpec version or base digest
- **THEN** the procedure requires maintenance authorization for the build, a dated validation entry and requalification of restricted installations

### Requirement: The runtime image starts Bash
The runtime image SHALL use `bash` as its entrypoint and SHALL contain no agent CLI. Its home SHALL be `/sandbox-home`, created in a layer with the `/workspace` working directory.

#### Scenario: Image entrypoint
- **WHEN** a container is started from the runtime image without a command
- **THEN** Bash runs with `HOME=/sandbox-home`

#### Scenario: No agent CLI
- **WHEN** the unit suite inspects the image recipe
- **THEN** it finds no agent CLI package such as `@anthropic-ai/claude-code`

## REMOVED Requirements

### Requirement: Pinned CLI matches the tested policy version
**Reason**: The reference image installs no agent CLI, and its policy file declares no provider profiles, so there is no CLI version to match.
**Migration**: Agent wrappers keep this requirement for their own CLI and policy.

### Requirement: Version updates follow explicit maintenance
**Reason**: The reference image has no agent CLI whose endpoint inventory needs revalidation.
**Migration**: See "Pinned input updates follow explicit maintenance".
