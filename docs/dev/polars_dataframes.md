# Polars DataFrame Patterns (Project Conventions)

This repo prefers Polars for tabular transforms and PyArrow for IO. Follow these patterns for consistency and correctness.

## Construction

- Row lists: pass `orient="row"` to avoid orientation warnings and make intent explicit.
  - `pl.DataFrame(rows, schema=[...], orient="row")`
- Dicts of lists: default (column) orientation is fine.
- From pandas: `pl.from_pandas(df)` to preserve types; avoid implicit casts.
- Set dtypes explicitly for important columns (IDs, dates, numerics) to prevent accidental up/down-casts.

## Transform Style

- Use expression APIs and `with_columns`/`select` over Python loops.
- Normalize strings with `.str.strip()` and validate keys early.
- For IDs: avoid numeric casts; store as text if any leading zeros or formatting (e.g., `gsis_id`).
- Use `coalesce()` for fallback keys (e.g., `coalesce(gsis_id, player_id)`).

## IO & Storage

- Reading: prefer `scan_parquet()`/`scan_csv()` for lazy pipelines; `read_*` only for small eager steps.
- Writing: use the storage helper for cloud/local transparency:
  - `from ingest.common.storage import write_parquet_any`
  - This supports both local paths and `gs://` URIs via PyArrow FS.

## Types & Nulls

- Be explicit with types for partition keys and primary keys.
- Use `fill_null` or `coalesce` to enforce non-null keys before writes.
- Avoid implicit numeric-to-string or string-to-numeric casts unless verified.

## Testing

- Construct small deterministic frames in tests; assert key coverage and schemas.
- Silence orientation warnings by using `orient="row"` when building from row lists.

## When to Convert

- To Arrow: `df.to_arrow()` when interoperating with PyArrow/Parquet APIs.
- To pandas: only for library compatibility; prefer staying in Polars for transforms.
