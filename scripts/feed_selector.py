"""Select a diverse set of seed GTFS feeds from the Mobility Database catalog."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from scripts.catalog_builder import download_catalog, load_catalog
from scripts.config import CATALOG_DIR, SEED_FEEDS_PATH, get_logger

logger = get_logger(__name__)


@dataclass
class SeedFeed:
    """A curated GTFS feed selected for the training dataset."""

    feed_id: str
    provider: str
    country_code: str
    subdivision: str
    municipality: str
    download_url: str
    license_url: str
    status: str
    category: str  # "large", "medium", "small"
    selected_reason: str


# Target agencies for diverse coverage
# Each entry: (search_term for provider name, country_code, category, reason)
TARGET_AGENCIES: list[tuple[str, str, str, str]] = [
    # Large agencies — complex networks, rich data
    ("Los Angeles County Metropolitan", "US", "large", "LA Metro — major US transit system"),
    ("Chicago Transit Authority", "US", "large", "Chicago CTA — major US grid network"),
    ("Massachusetts Bay Transportation", "US", "large", "Boston MBTA — large US rail+bus system"),
    ("Transport For London", "GB", "large", "TfL — one of the world's largest transit networks"),
    ("Verkehrsverbund Berlin-Brandenburg", "DE", "large", "Berlin VBB — major European transit"),
    # Medium agencies — good variety across continents
    ("Toronto Transit Commission", "CA", "medium", "Toronto TTC — major Canadian agency"),
    ("Société de transport de Montréal", "CA", "medium", "Montreal STM — major Canadian agency"),
    ("STIB", "BE", "medium", "Brussels STIB — European capital transit"),
    ("Auckland Transport", "NZ", "medium", "Auckland — Oceania mid-size city"),
    ("São Paulo Transporte", "BR", "medium", "São Paulo — largest South American transit"),
    # Small agencies — simpler networks, different patterns
    ("Valley Metro", "US", "small", "Phoenix — US Sun Belt mid-size transit"),
    ("Capital Metro", "US", "small", "Austin — growing US transit system"),
    ("TriMet", "US", "small", "Portland TriMet — mid-size US city"),
    ("Transperth", "AU", "small", "Perth — smaller Australian city transit"),
    ("Rejseplanen", "DK", "small", "Denmark national transit data"),
]


def find_feed_in_catalog(
    df: pd.DataFrame,
    search_term: str,
    country_code: str,
) -> pd.Series | None:
    """Find a feed matching the search term and country code."""
    mask = pd.Series([True] * len(df), index=df.index)

    if "location.country_code" in df.columns:
        mask &= df["location.country_code"] == country_code

    if "provider" in df.columns:
        mask &= df["provider"].str.contains(search_term, case=False, na=False)

    matches = df[mask]

    if matches.empty:
        return None

    # Prefer the first match (catalog is typically sorted by relevance)
    return matches.iloc[0]


def select_seed_feeds(df: pd.DataFrame) -> list[SeedFeed]:
    """Select diverse seed feeds from the catalog based on target agencies."""
    selected: list[SeedFeed] = []

    for search_term, country_code, category, reason in TARGET_AGENCIES:
        row = find_feed_in_catalog(df, search_term, country_code)

        if row is None:
            logger.warning(
                "Could not find feed for '%s' in %s — skipping", search_term, country_code
            )
            continue

        feed = SeedFeed(
            feed_id=str(row.get("mdb_source_id", row.name)),
            provider=str(row.get("provider", "Unknown")),
            country_code=str(row.get("location.country_code", country_code)),
            subdivision=str(row.get("location.subdivision_name", "")),
            municipality=str(row.get("location.municipality", "")),
            download_url=str(row.get("urls.direct_download", "")),
            license_url=str(row.get("urls.license", "")),
            status=str(row.get("status", "active")),
            category=category,
            selected_reason=reason,
        )
        selected.append(feed)
        logger.info("Selected: %s (%s) [%s]", feed.provider, feed.country_code, category)

    return selected


def save_seed_feeds(feeds: list[SeedFeed], path: Path | None = None) -> Path:
    """Save selected feeds to seed_feeds.json."""
    output_path = path or SEED_FEEDS_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = [asdict(feed) for feed in feeds]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Saved %d seed feeds to %s", len(feeds), output_path)
    return output_path


if __name__ == "__main__":
    # Ensure catalog is downloaded
    download_catalog()

    # Load filtered catalog
    catalog = load_catalog()

    # Select diverse feeds
    feeds = select_seed_feeds(catalog)

    if not feeds:
        logger.error("No feeds selected — check catalog and target agencies")
        raise SystemExit(1)

    # Save to JSON
    save_seed_feeds(feeds)

    # Print summary
    print("\n" + "=" * 60)
    print("SELECTED SEED FEEDS")
    print("=" * 60)
    for i, feed in enumerate(feeds, 1):
        print(f"\n{i:2d}. {feed.provider}")
        print(f"    Country:  {feed.country_code} / {feed.subdivision}")
        print(f"    Category: {feed.category}")
        print(f"    Feed ID:  {feed.feed_id}")
        print(f"    URL:      {feed.download_url[:80]}...")
        print(f"    Reason:   {feed.selected_reason}")

    print(f"\nTotal: {len(feeds)} feeds selected")
    print(f"  Large:  {sum(1 for f in feeds if f.category == 'large')}")
    print(f"  Medium: {sum(1 for f in feeds if f.category == 'medium')}")
    print(f"  Small:  {sum(1 for f in feeds if f.category == 'small')}")
    print(f"\nSaved to: {SEED_FEEDS_PATH}")
