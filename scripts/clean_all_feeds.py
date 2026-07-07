"""Clean all downloaded GTFS feeds and generate a summary report."""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.clean_feed import FeedCleaningResult, clean_feed
from scripts.config import CLEANED_DIR, RAW_DIR, get_logger

logger = get_logger(__name__)


def discover_feeds(raw_dir: Path | None = None) -> list[tuple[str, dict]]:
    """Find all downloaded feeds with valid metadata.

    Returns:
        List of (feed_id, metadata_dict) tuples.
    """
    raw = raw_dir or RAW_DIR
    feeds = []

    for feed_dir in sorted(raw.iterdir()):
        if not feed_dir.is_dir() or not feed_dir.name.startswith("mdb-"):
            continue

        zip_path = feed_dir / "gtfs.zip"
        metadata_path = feed_dir / "metadata.json"

        if not zip_path.exists():
            continue

        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, encoding="utf-8") as f:
                metadata = json.load(f)

        # Extract feed_id (strip "mdb-" prefix)
        feed_id = feed_dir.name.replace("mdb-", "")
        feeds.append((feed_id, metadata))

    return feeds


def clean_all_feeds(
    raw_dir: Path | None = None,
    out_dir: Path | None = None,
    feed_ids: list[str] | None = None,
    force: bool = False,
) -> list[FeedCleaningResult]:
    """Clean all (or selected) feeds."""
    raw = raw_dir or RAW_DIR
    out = out_dir or CLEANED_DIR
    out.mkdir(parents=True, exist_ok=True)

    all_feeds = discover_feeds(raw)

    if feed_ids:
        all_feeds = [(fid, meta) for fid, meta in all_feeds if fid in feed_ids]

    total = len(all_feeds)
    if total == 0:
        logger.warning("No feeds found to clean")
        return []

    logger.info("Cleaning %d feeds", total)
    results: list[FeedCleaningResult] = []

    for i, (feed_id, metadata) in enumerate(all_feeds, 1):
        provider = metadata.get("provider", "Unknown")
        logger.info("[%d/%d] %s (%s)", i, total, provider, feed_id)

        start = time.time()
        result = clean_feed(feed_id, raw_dir=raw, out_dir=out, force=force)
        elapsed = time.time() - start

        results.append(result)
        status = "OK" if result.success else "FAILED"
        logger.info("[%d/%d] %s in %.1fs", i, total, status, elapsed)

    return results


def generate_report(
    results: list[FeedCleaningResult],
    out_dir: Path | None = None,
) -> Path:
    """Write cleaning_report.json with aggregate stats."""
    out = out_dir or CLEANED_DIR
    report_path = out / "cleaning_report.json"

    # Aggregate stats
    total_routes = 0
    total_stops = 0
    total_trips = 0
    total_stop_times = 0

    feeds_detail = {}
    for r in results:
        feeds_detail[f"mdb-{r.feed_id}"] = {
            "provider": r.provider,
            "country_code": r.country_code,
            "success": r.success,
            "files": r.file_stats,
            "integrity_issues": r.integrity_issues,
            "errors": r.errors,
            "warnings": r.warnings,
        }

        for filename, stats in r.file_stats.items():
            rows = stats.get("rows_cleaned", 0)
            if filename == "routes.txt":
                total_routes += rows
            elif filename == "stops.txt":
                total_stops += rows
            elif filename == "trips.txt":
                total_trips += rows
            elif filename == "stop_times.txt":
                total_stop_times += rows

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_feeds": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "aggregate_stats": {
            "total_routes": total_routes,
            "total_stops": total_stops,
            "total_trips": total_trips,
            "total_stop_times": total_stop_times,
        },
        "feeds": feeds_detail,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Report saved to %s", report_path)
    return report_path


def print_summary(results: list[FeedCleaningResult]) -> None:
    """Print a summary of cleaning results."""
    succeeded = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\n" + "=" * 60)
    print("CLEANING SUMMARY")
    print("=" * 60)
    print(f"  Successful: {len(succeeded)}")
    print(f"  Failed:     {len(failed)}")

    if failed:
        print("\nFailed feeds:")
        for r in failed:
            print(f"  - mdb-{r.feed_id} ({r.provider}): {r.errors}")

    # Aggregate stats
    total_routes = 0
    total_stops = 0
    total_trips = 0
    total_stop_times = 0

    for r in succeeded:
        for filename, stats in r.file_stats.items():
            rows = stats.get("rows_cleaned", 0)
            if filename == "routes.txt":
                total_routes += rows
            elif filename == "stops.txt":
                total_stops += rows
            elif filename == "trips.txt":
                total_trips += rows
            elif filename == "stop_times.txt":
                total_stop_times += rows

    print(f"\nAggregate data:")
    print(f"  Routes:     {total_routes:,}")
    print(f"  Stops:      {total_stops:,}")
    print(f"  Trips:      {total_trips:,}")
    print(f"  Stop times: {total_stop_times:,}")


def main() -> None:
    """Entry point with CLI arguments."""
    parser = argparse.ArgumentParser(description="Clean GTFS feeds")
    parser.add_argument(
        "--feed-id", nargs="+", help="Specific feed ID(s) to clean"
    )
    parser.add_argument(
        "--force", action="store_true", help="Re-clean feeds that already have output"
    )
    parser.add_argument(
        "--raw-dir", type=Path, default=None, help="Override raw data directory"
    )
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="Override output directory"
    )
    args = parser.parse_args()

    results = clean_all_feeds(
        raw_dir=args.raw_dir,
        out_dir=args.out_dir,
        feed_ids=args.feed_id,
        force=args.force,
    )

    report_path = generate_report(results, out_dir=args.out_dir)
    print_summary(results)
    print(f"\nDetailed report: {report_path}")


if __name__ == "__main__":
    main()
