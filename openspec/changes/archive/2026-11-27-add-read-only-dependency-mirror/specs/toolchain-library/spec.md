# Spec Delta

## ADDED Requirements

### Requirement: Recipes can name dependency mirror profiles
Schema 2 recipes SHALL accept an optional bounded `registries` array of profile names, including for image-only toolchains. The library SHALL expose the names as optional index metadata. An absent declaration SHALL be treated as empty. A recipe SHALL have no authority to define an upstream or select the network mode.

#### Scenario: Valid declaration and legacy recipe
- **WHEN** a schema 2 recipe names profiles or a recipe predates the field
- **THEN** the library installs it under the existing schema and offline check rules
- **AND** the index and operator guidance show the optional names when declared

#### Scenario: Destination supplied in a recipe
- **WHEN** a recipe specifies an upstream URL, credential or invalid name in `registries`
- **THEN** validation fails before fetching sources and the installed library is unchanged

#### Scenario: Default toolchain in a mirror-enabled session
- **WHEN** a default toolchain eligible for the session declares an installed profile
- **THEN** the launcher includes that profile in the session's launch-time selection
- **AND** an ineligible or non-default toolchain supplies no automatic activation

#### Scenario: Library disabled or offline
- **WHEN** the library is disabled or the session uses offline networking
- **THEN** recipes add no mirror profile or network access to that session
