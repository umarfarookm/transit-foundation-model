"""Download and filter the Mobility Database CSV catalog."""

from pathlib import Path

import pandas as pd
import requests

from scripts.config import (
    CATALOG_DIR,
    CHUNK_SIZE,
    MOBILITY_DB_CSV_PATH,
    MOBILITY_DB_CSV_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
    get_logger,
)

logger = get_logger(__name__)


def download_catalog(force: bool = False) -> Path:
    """Download the Mobility Database feeds CSV catalog.

    Args:
        force: Re-download even if the file already exists.

    Returns:
        Path to the downloaded CSV file.
    """
    if MOBILITY_DB_CSV_PATH.exists() and not force:
        logger.info("Catalog already exists at %s, skipping download (use force=True to refresh)",
                     MOBILITY_DB_CSV_PATH)
        return MOBILITY_DB_CSV_PATH

    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading Mobility Database catalog from %s", MOBILITY_DB_CSV_URL)
    response = requests.get(
        MOBILITY_DB_CSV_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
        stream=True,
    )
    response.raise_for_status()

    total_size = 0
    with open(MOBILITY_DB_CSV_PATH, "wb") as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            f.write(chunk)
            total_size += len(chunk)

    logger.info("Catalog saved to %s (%s bytes)", MOBILITY_DB_CSV_PATH, f"{total_size:,}")
    return MOBILITY_DB_CSV_PATH


def load_catalog(csv_path: Path | None = None) -> pd.DataFrame:
    """Load the Mobility Database CSV and filter to usable GTFS feeds.

    Filters:
    - data_type == "gtfs" (static feeds only)
    - Excludes "inactive" status (keeps active, deprecated, NaN, development)
    - Has a direct download URL
    - No authentication required (auth_type is NaN or 0)

    Returns:
        Filtered DataFrame of GTFS feeds.
    """
    path = csv_path or MOBILITY_DB_CSV_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Catalog not found at {path}. Run download_catalog() first."
        )

    logger.info("Loading catalog from %s", path)
    df = pd.read_csv(path, low_memory=False)
    total = len(df)
    logger.info("Total entries in catalog: %s", f"{total:,}")

    # Filter to GTFS static feeds only
    if "data_type" in df.columns:
        df = df[df["data_type"] == "gtfs"]

    # Exclude inactive feeds (most feeds have NaN status — those are usable)
    if "status" in df.columns:
        df = df[df["status"] != "inactive"]

    # Must have a direct download URL
    if "urls.direct_download" in df.columns:
        df = df[df["urls.direct_download"].notna() & (df["urls.direct_download"] != "")]

    # Skip feeds requiring authentication (auth_type 1 and 2 need keys)
    if "urls.authentication_type" in df.columns:
        df = df[df["urls.authentication_type"].isna() | (df["urls.authentication_type"] == 0)]

    filtered = len(df)
    logger.info("Usable GTFS feeds after filtering: %s (from %s total)", f"{filtered:,}",
                f"{total:,}")
    return df.reset_index(drop=True)


def get_feed_stats(df: pd.DataFrame) -> dict:
    """Generate summary statistics from the catalog DataFrame."""
    stats: dict = {
        "total_feeds": len(df),
    }

    if "location.country_code" in df.columns:
        country_counts = df["location.country_code"].value_counts()
        stats["countries"] = len(country_counts)
        stats["top_countries"] = country_counts.head(20).to_dict()

    if "provider" in df.columns:
        stats["unique_providers"] = df["provider"].nunique()

    return stats


if __name__ == "__main__":
    import json

    # Download catalog
    download_catalog()

    # Load and filter
    feeds = load_catalog()

    # Print stats
    stats = get_feed_stats(feeds)
    print("\n" + "=" * 60)
    print("MOBILITY DATABASE CATALOG STATS")
    print("=" * 60)
    print(f"Total usable GTFS feeds: {stats['total_feeds']:,}")
    print(f"Countries represented:   {stats.get('countries', 'N/A')}")
    print(f"Unique providers:        {stats.get('unique_providers', 'N/A')}")

    if "top_countries" in stats:
        print("\nTop 20 countries by feed count:")
        for country, count in stats["top_countries"].items():
            print(f"  {country}: {count}")

    print("\nSample feeds:")
    cols = ["provider", "location.country_code", "urls.direct_download"]
    available_cols = [c for c in cols if c in feeds.columns]
    print(feeds[available_cols].head(10).to_string(index=False))
