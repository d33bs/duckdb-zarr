# Community Extension Release

This project is set up to publish through DuckDB's community extension repository.
DuckDB's process is descriptor-driven: submit a PR to `duckdb/community-extensions`
with this repository's `description.yml`, and the community repository builds it
with the same `extension-ci-tools` distribution workflow used here.

## Local Release Gate

Run the local checks before opening the community PR:

```sh
make release-check
make test_release
```

`make release-check` verifies the release-critical metadata that is easy to drift
in a Rust C API extension:

- `Makefile` `TARGET_DUCKDB_VERSION`
- `.github/workflows/MainDistributionPipeline.yml` `duckdb_version`
- `Cargo.toml` exact `duckdb` crate pin
- `description.yml` `language`, `build`, `requires_toolchains`, and excluded
  platforms

For the final community PR, also run:

```sh
python3 scripts/check_release_ready.py --strict-community-ref
```

That strict mode fails until `description.yml` `repo.ref` is an immutable release
tag such as `v0.1.0` or a 40-character commit hash. Do not submit `ref: main`.

For release automation, leave the checked-in descriptor at `ref: main` and
render the community descriptor for a tag:

```sh
make render-community-descriptor REF=v0.1.0
```

The rendered file is written to
`build/community-extensions/extensions/duckdb_zarr/description.yml` with
`repo.ref` set to the release tag.

## GitHub Release Automation

Publishing a GitHub Release runs `.github/workflows/community-release.yml`.
That workflow:

1. Renders a community descriptor for the release tag.
2. Validates the generated descriptor in strict mode.
3. Uploads the descriptor as a workflow artifact.

The workflow intentionally does not store or use a cross-repository token. A
maintainer downloads the artifact and opens the PR to
`duckdb/community-extensions` manually. This keeps release automation read-only
inside this repository while still making the submitted descriptor reproducible.

## Descriptor Notes

The descriptor intentionally marks this as a Rust cargo extension and requests
the extra toolchains that the community CI must install:

```yaml
extension:
  language: Rust
  build: cargo
  requires_toolchains: "rust;python3"
```

The descriptor excludes `wasm_mvp`, `wasm_eh`, `wasm_threads`, and
`linux_amd64_musl`. The local distribution workflow uses the same exclusion set.
Re-enable platforms only after the CI build and SQLLogic tests pass for them.

## Submission Steps

1. Ensure `main` is green for `Main Extension Distribution Pipeline` and
   `Rust quality`.
2. Update `CHANGELOG.md`, `Cargo.toml` version, `pyproject.toml` version, and
   the `description.yml` version.
3. Create and publish a GitHub Release with a tag matching the project version,
   such as `v0.1.0`.
4. Download the validated descriptor artifact from the `Community Extension
   Release` workflow.
5. Open a PR against `duckdb/community-extensions` adding or updating
   `extensions/duckdb_zarr/description.yml` with that artifact.

After the PR is merged and built by DuckDB's community infrastructure, users can
install with:

```sql
INSTALL duckdb_zarr FROM community;
LOAD duckdb_zarr;
```

## DuckDB Version Policy

DuckDB community extensions are distributed for DuckDB's latest stable release.
This extension currently sets `USE_UNSTABLE_C_API=1`, so the produced binary is
not forward-compatible across DuckDB patch releases: the loader expects the exact
DuckDB version stamped into the extension metadata.

That means a DuckDB bump must update all version sites in one reviewed change:

- `Makefile` `TARGET_DUCKDB_VERSION`
- `.github/workflows/MainDistributionPipeline.yml` `duckdb_version`
- `Cargo.toml` exact `duckdb` crate pin
- `Cargo.lock`

The local release gate checks the first three. `Cargo.lock` should change when
`cargo update -p duckdb --precise <crate-version>` is run.

The `duckdb` crate version used here encodes the DuckDB version. For the current
pin, DuckDB `v1.5.4` maps to:

```toml
duckdb = { version = "=1.10504.0", features = ["loadable-extension"] }
```

Use the automated `DuckDB Version Drift` workflow for routine patch-line bumps.
Treat major or minor DuckDB bumps as manual migrations: update the pins, rebuild,
run `make lint`, and run `make test_release` before changing `description.yml`
for community publication.

## Stable vs. Current DuckDB Main

Near DuckDB releases, `duckdb/community-extensions` can test extensions against
both the latest stable release and DuckDB `main`. If one commit cannot support
both, maintain two refs:

```yaml
repo:
  github: xqlsystems/duckdb-zarr
  ref: <stable-compatible-tag-or-commit>
  ref_next: <duckdb-main-compatible-commit>
```

Use `ref` for the commit that works with the latest stable DuckDB release. Use
`ref_next` only when DuckDB `main` needs source changes that should not replace
the stable build yet. After DuckDB releases, the community repository can promote
the `ref_next` commit to `ref`.
