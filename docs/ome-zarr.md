# Querying OME-Zarr

OME-Zarr images commonly contain several resolution levels and nested label
arrays. The examples below run against this repo's small synthetic fixture
(`make generate_fixtures` first). Start by listing the available arrays:

```sql
SELECT name, dims, shape, dtype
FROM read_zarr_metadata('test/fixtures/bioimage/ome_zarr/synthetic_multichannel.ome.zarr');
```

The `array_path` argument is optional. Use it when a store has multiple
resolution levels, nested labels, or otherwise ambiguous array groups. The path
is the same store-relative path reported by `read_zarr_metadata`.

Then select a resolution level and aggregate by channel:

```sql
SELECT c, AVG("0") AS mean_intensity
FROM read_zarr('test/fixtures/bioimage/ome_zarr/synthetic_multichannel.ome.zarr', array_path='0')
GROUP BY c;
```

Here, `0` is the conventional path for the highest-resolution level. Xarray
dimension names such as `c`, `y`, and `x` become SQL columns — add a
`WHERE y BETWEEN ... AND x BETWEEN ...` clause to aggregate a sub-region. Numeric
and nested array names must be double-quoted when referenced as columns.

Nested label arrays use the same selector:

```sql
SELECT "labels/nuclei/0" AS label, COUNT(*) AS pixels
FROM read_zarr('test/fixtures/bioimage/ome_zarr/synthetic_multichannel.ome.zarr', array_path='labels/nuclei/0')
WHERE "labels/nuclei/0" > 0
GROUP BY label;
```
