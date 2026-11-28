# Spec Delta

## ADDED Requirements

### Requirement: Self-contained image build contexts
Every image build context shipped by a release SHALL admit through its `.containerignore` allowlist every source file copied by its `Containerfile`, and every Python module copied into the proxy or runtime image SHALL have its local module imports present in that image. Setup SHALL include `network/.containerignore` in the proxy image reuse inputs so build-context filter changes trigger a rebuild.

#### Scenario: Proxy image build context admits all mirror modules
- **WHEN** setup builds the egress proxy image from `network/Containerfile`
- **THEN** `network/.containerignore` admits `Containerfile`, `.containerignore`, and every module named in `COPY` (including `mirror.py`, `mirror_policy.py`, `mirror_cache.py`, and `mirror_metadata.py`)
- **AND** every local module imported by those proxy files is copied into `/opt/sandbox-egress/`

#### Scenario: Runtime image includes modules imported by copied egress code
- **WHEN** the runtime image is built from `Containerfile`
- **THEN** `.containerignore` admits every file copied by `Containerfile`
- **AND** `Containerfile` copies `network/revisions.py` alongside `network/relay.py` and `network/mux.py` so `/opt/sandbox-egress/mux.py` resolves its local imports inside the built image

#### Scenario: Proxy image reuse invalidates when the build-context allowlist changes
- **WHEN** `network/.containerignore` differs between the previous release and the candidate release during setup
- **THEN** setup does not reuse the previous proxy image identity and builds a fresh proxy image
