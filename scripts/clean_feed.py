"""Clean and normalize a single GTFS feed into Parquet files."""

import io
import json
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts.config import CLEANED_DIR, RAW_DIR, get_logger
from scripts.gtfs_schema import GTFS_SCHEMAS, GtfsFileSpec
from scripts.validate_feed import _find_in_zip

logger = get_logger(__name__)

CHUNK_SIZE_ROWS = 500_000


@dataclass
class FileCleaningStats:
    """Statistics from cleaning one GTFS file."""

    rows_raw: int = 0
    rows_cleaned: int = 0
    duplicates_removed: int = 0
    columns_kept: list[str] = field(default_factory=list)
    columns_dropped: list[str] = field(default_factory=list)
    chunked: bool = False


@dataclass
class FeedCleaningResult:
    """Statistics and status from cleaning one feed."""

    feed_id: str
    provider: str = ""
    country_code: str = ""
    success: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_stats: dict[str, dict] = field(default_factory=dict)
    integrity_issues: dict[str, int] = field(default_factory=dict)


def clean_feed(
    feed_id: str,
    raw_dir: Path | None = None,
    out_dir: Path | None = None,
    force: bool = False,
) -> FeedCleaningResult:
    """Clean a single GTFS feed end-to-end.

    Reads the raw ZIP, normalizes each file to canonical columns,
    coerces dtypes, deduplicates, checks referential integrity,
    and writes Parquet files.
    """
    raw = raw_dir or RAW_DIR
    out = out_dir or CLEANED_DIR

    feed_dir = raw / f"mdb-{feed_id}"
    zip_path = feed_dir / "gtfs.zip"
    metadata_path = feed_dir / "metadata.json"
    output_dir = out / f"mdb-{feed_id}"

    result = FeedCleaningResult(feed_id=feed_id)

    # Load metadata
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)
        result.provider = metadata.get("provider", "")
        result.country_code = metadata.get("country_code", "")

    # Check if already cleaned
    stats_path = output_dir / "feed_stats.json"
    if stats_path.exists() and not force:
        logger.info("[%s] Already cleaned, skipping (use --force to re-clean)", feed_id)
        result.success = True
        return result

    if not zip_path.exists():
        result.errors.append(f"ZIP not found: {zip_path}")
        return result

    logger.info("[%s] Cleaning: %s (%s)", feed_id, result.provider, result.country_code)
    output_dir.mkdir(parents=True, exist_ok=True)

    tables: dict[str, pd.DataFrame] = {}

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            all_names = zf.namelist()

            for filename, spec in GTFS_SCHEMAS.items():
                actual_path = _find_in_zip(all_names, filename)

                if actual_path is None:
                    if spec.is_required_file:
                        result.errors.append(f"Missing required file: {filename}")
                    continue

                file_info = zf.getinfo(actual_path)
                parquet_path = output_dir / spec.parquet_name

                # Use chunked processing for large files
                if file_info.file_size > spec.chunk_threshold_bytes:
                    stats = _write_parquet_chunked(zf, actual_path, spec, parquet_path)
                    stats.chunked = True
                    result.file_stats[filename] = asdict(stats)
                    logger.info(
                        "[%s] %s: %s rows (chunked)", feed_id, filename,
                        f"{stats.rows_cleaned:,}",
                    )
                    continue

                # Standard (in-memory) processing
                df = _read_gtfs_csv(zf, actual_path, spec)
                if df is None or df.empty:
                    result.warnings.append(f"{filename} is empty")
                    continue

                raw_rows = len(df)
                df, dropped = _normalize_columns(df, spec)
                df = _coerce_dtypes(df, spec)
                df, dupes = _deduplicate(df, spec)

                # Write Parquet
                _write_parquet(df, parquet_path)

                stats = FileCleaningStats(
                    rows_raw=raw_rows,
                    rows_cleaned=len(df),
                    duplicates_removed=dupes,
                    columns_kept=list(df.columns),
                    columns_dropped=dropped,
                )
                result.file_stats[filename] = asdict(stats)
                tables[filename] = df

                logger.info(
                    "[%s] %s: %s -> %s rows, %d cols dropped",
                    feed_id, filename, f"{raw_rows:,}", f"{len(df):,}", len(dropped),
                )

        # Referential integrity checks
        result.integrity_issues = _check_referential_integrity(tables, output_dir)
        if result.integrity_issues:
            for issue, count in result.integrity_issues.items():
                if count > 0:
                    result.warnings.append(f"{issue}: {count}")

        # Write per-feed stats
        feed_stats = {
            "feed_id": feed_id,
            "provider": result.provider,
            "country_code": result.country_code,
            "files": result.file_stats,
            "integrity_issues": result.integrity_issues,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(feed_stats, f, indent=2, ensure_ascii=False)

        result.success = len(result.errors) == 0
        status = "OK" if result.success else "ERRORS"
        logger.info("[%s] Done (%s): %d files cleaned", feed_id, status, len(result.file_stats))

    except Exception as e:
        result.errors.append(f"Unexpected error: {e}")
        logger.error("[%s] Failed: %s", feed_id, e)

    return result


def _read_gtfs_csv(
    zf: zipfile.ZipFile,
    actual_path: str,
    spec: GtfsFileSpec,
) -> pd.DataFrame | None:
    """Read a single GTFS CSV from a ZIP file."""
    try:
        with zf.open(actual_path) as raw:
            text_stream = io.TextIOWrapper(raw, encoding="utf-8-sig")
            df = pd.read_csv(
                text_stream,
                dtype=str,
                keep_default_na=False,
                na_values=[""],
            )
        # Strip whitespace from column names (some feeds have leading spaces)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        logger.warning("Failed to read %s: %s", actual_path, e)
        return None


def _normalize_columns(
    df: pd.DataFrame,
    spec: GtfsFileSpec,
) -> tuple[pd.DataFrame, list[str]]:
    """Select canonical columns, add missing required ones, drop non-spec ones."""
    source_cols = set(df.columns)
    canonical = set(spec.all_columns)

    # Columns to drop (in source but not in spec)
    dropped = sorted(source_cols - canonical)

    # Columns to keep (in both source and spec)
    keep = [col for col in spec.all_columns if col in source_cols]

    df = df[keep].copy()

    # Add missing required columns as NA
    for col in spec.required_columns:
        if col not in df.columns:
            df[col] = pd.NA

    return df, dropped


def _coerce_dtypes(df: pd.DataFrame, spec: GtfsFileSpec) -> pd.DataFrame:
    """Cast columns to canonical dtypes, coercing errors to NA."""
    for col, dtype in spec.dtypes.items():
        if col not in df.columns:
            continue
        if dtype == "str":
            df[col] = df[col].astype("string")
        elif dtype == "float64":
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
        elif dtype in ("Int8", "Int16", "Int32"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(dtype)

    return df


def _deduplicate(
    df: pd.DataFrame,
    spec: GtfsFileSpec,
) -> tuple[pd.DataFrame, int]:
    """Remove duplicate rows based on primary key."""
    if not spec.primary_key:
        return df, 0

    pk_cols = [col for col in spec.primary_key if col in df.columns]
    if not pk_cols:
        return df, 0

    before = len(df)
    df = df.drop_duplicates(subset=pk_cols, keep="first")
    dupes = before - len(df)
    return df, dupes


def _check_referential_integrity(
    tables: dict[str, pd.DataFrame],
    output_dir: Path,
) -> dict[str, int]:
    """Check foreign key relationships between tables."""
    issues: dict[str, int] = {}

    # trip_id in stop_times must exist in trips
    if "trips.txt" in tables:
        trip_ids = set(tables["trips.txt"]["trip_id"].dropna())

        # stop_times might be chunked — read trip_id column from Parquet
        st_path = output_dir / "stop_times.parquet"
        if "stop_times.txt" in tables:
            st_trip_ids = set(tables["stop_times.txt"]["trip_id"].dropna())
        elif st_path.exists():
            st_trip_ids = set(
                pq.read_table(st_path, columns=["trip_id"]).column("trip_id").to_pylist()
            )
        else:
            st_trip_ids = set()

        orphan = st_trip_ids - trip_ids
        issues["orphan_trip_ids_in_stop_times"] = len(orphan)

    # route_id in trips must exist in routes
    if "trips.txt" in tables and "routes.txt" in tables:
        route_ids = set(tables["routes.txt"]["route_id"].dropna())
        trip_route_ids = set(tables["trips.txt"]["route_id"].dropna())
        issues["orphan_route_ids_in_trips"] = len(trip_route_ids - route_ids)

    # stop_id in stop_times must exist in stops
    if "stops.txt" in tables:
        stop_ids = set(tables["stops.txt"]["stop_id"].dropna())

        if "stop_times.txt" in tables:
            st_stop_ids = set(tables["stop_times.txt"]["stop_id"].dropna())
        elif (output_dir / "stop_times.parquet").exists():
            st_stop_ids = set(
                pq.read_table(
                    output_dir / "stop_times.parquet", columns=["stop_id"]
                ).column("stop_id").to_pylist()
            )
        else:
            st_stop_ids = set()

        issues["orphan_stop_ids_in_stop_times"] = len(st_stop_ids - stop_ids)

    # service_id in trips must exist in calendar or calendar_dates
    if "trips.txt" in tables:
        service_ids: set[str] = set()
        if "calendar.txt" in tables:
            service_ids |= set(tables["calendar.txt"]["service_id"].dropna())
        if "calendar_dates.txt" in tables:
            service_ids |= set(tables["calendar_dates.txt"]["service_id"].dropna())

        if service_ids:
            trip_svc_ids = set(tables["trips.txt"]["service_id"].dropna())
            issues["orphan_service_ids_in_trips"] = len(trip_svc_ids - service_ids)

    return issues


def _write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write DataFrame to Parquet with snappy compression."""
    df.to_parquet(path, engine="pyarrow", compression="snappy", index=False)


def _write_parquet_chunked(
    zf: zipfile.ZipFile,
    actual_path: str,
    spec: GtfsFileSpec,
    out_path: Path,
) -> FileCleaningStats:
    """Process a large GTFS CSV in chunks and write to Parquet incrementally."""
    stats = FileCleaningStats()
    writer: pq.ParquetWriter | None = None

    try:
        with zf.open(actual_path) as raw:
            text_stream = io.TextIOWrapper(raw, encoding="utf-8-sig")
            reader = pd.read_csv(
                text_stream,
                dtype=str,
                keep_default_na=False,
                na_values=[""],
                chunksize=CHUNK_SIZE_ROWS,
            )

            for chunk in reader:
                chunk.columns = chunk.columns.str.strip()
                stats.rows_raw += len(chunk)
                chunk, dropped = _normalize_columns(chunk, spec)
                chunk = _coerce_dtypes(chunk, spec)
                # Skip dedup across chunks for performance — within-chunk only
                chunk, dupes = _deduplicate(chunk, spec)
                stats.duplicates_removed += dupes
                stats.rows_cleaned += len(chunk)

                if not stats.columns_kept:
                    stats.columns_kept = list(chunk.columns)
                    stats.columns_dropped = dropped

                table = pa.Table.from_pandas(chunk, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(out_path, table.schema, compression="snappy")
                writer.write_table(table)

    finally:
        if writer is not None:
            writer.close()

    return stats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.clean_feed <feed_id>")
        sys.exit(1)

    feed_id = sys.argv[1]
    result = clean_feed(feed_id)

    print(f"\nFeed {feed_id}: {'OK' if result.success else 'FAILED'}")
    print(f"Provider: {result.provider} ({result.country_code})")
    print(f"Files cleaned: {len(result.file_stats)}")
    if result.errors:
        print(f"Errors: {result.errors}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")
    if result.integrity_issues:
        print(f"Integrity: {result.integrity_issues}")
