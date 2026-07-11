"""
HTTP integration tests for duckdb-zarr's remote reader.

Remote (HTTP/object) stores cannot list directories, so ``read_zarr`` enumerates
arrays from consolidated metadata. Two mechanisms are exercised here:

  * Zarr v2 — a separate ``.zmetadata`` object      (consolidated_v2_http.zarr)
  * Zarr v3 — a ``consolidated_metadata`` block      (consolidated_v3_http.zarr)

Both fixtures carry the same 8×6×12 (time, lat, lon) grid, so the assertions are
shared across the two remote paths. The stores are served over the loopback
``http.server`` started by the ``http_server_url`` fixture in conftest.py.

Run with:
    make test_http_debug
    # or directly:
    pytest test/test_http_integration.py \
        --extension build/debug/zarr.duckdb_extension
"""
import pathlib

import duckdb
import pytest

ROOT = pathlib.Path(__file__).parent.parent

# Store-relative path (under the repo root the http server is rooted at) → id.
FIXTURES = {
    "v2_zmetadata": "test/fixtures/xarray_tutorial/consolidated_v2_http.zarr",
    "v3_consolidated": "test/fixtures/xarray_tutorial/consolidated_v3_http.zarr",
}


@pytest.fixture(scope="module")
def con(extension_path):
    """DuckDB connection with the zarr extension loaded, shared across the module."""
    c = duckdb.connect(config={"allow_unsigned_extensions": True})
    c.execute(f"LOAD '{extension_path}'")
    return c


@pytest.fixture(params=sorted(FIXTURES), ids=sorted(FIXTURES))
def store(request, http_server_url):
    """Full HTTP URL for each consolidated fixture (parametrized over v2 and v3)."""
    rel = FIXTURES[request.param]
    if not (ROOT / rel).exists():
        pytest.fail(
            f"HTTP fixture not found: {rel}\n"
            "Run: python scripts/generate_fixtures.py"
        )
    return f"{http_server_url}/{rel}"


# ── read_zarr over HTTP ─────────────────────────────────────────────────────

def test_row_count(con, store):
    assert con.execute(f"SELECT COUNT(*) FROM read_zarr('{store}')").fetchone()[0] == 576


def test_distinct_coords(con, store):
    row = con.execute(
        f"SELECT COUNT(DISTINCT lat), COUNT(DISTINCT lon) FROM read_zarr('{store}')"
    ).fetchone()
    assert row == (6, 12)


def test_lat_range(con, store):
    row = con.execute(f"SELECT MIN(lat), MAX(lat) FROM read_zarr('{store}')").fetchone()
    assert row == (-90.0, 90.0)


def test_temperature_non_null(con, store):
    got = con.execute(
        f"SELECT COUNT(*) FROM read_zarr('{store}') WHERE temperature IS NOT NULL"
    ).fetchone()[0]
    assert got == 576


def test_projection_pushdown(con, store):
    """Projecting a single column must still return correct values over HTTP."""
    got = con.execute(
        f"SELECT COUNT(DISTINCT lat) FROM (SELECT lat FROM read_zarr('{store}'))"
    ).fetchone()[0]
    assert got == 6


# ── replacement scan (bare path ending in .zarr) ────────────────────────────

def test_replacement_scan(con, store):
    assert con.execute(f"SELECT COUNT(*) FROM '{store}'").fetchone()[0] == 576


# ── read_zarr_metadata over HTTP ────────────────────────────────────────────

def test_metadata_roles(con, store):
    rows = con.execute(
        f"SELECT name, role FROM read_zarr_metadata('{store}') ORDER BY name"
    ).fetchall()
    assert rows == [
        ("lat", "coord"),
        ("lon", "coord"),
        ("temperature", "data"),
        ("time", "coord"),
    ]
