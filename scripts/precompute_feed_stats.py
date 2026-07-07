"""Stage 1: Pre-compute per-feed statistics from cleaned Parquet files.

Extracts lightweight JSON summaries that the dataset generator uses
to create instruction/response pairs without loading 77M+ rows.
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from scripts.config import CLEANED_DIR, get_logger

logger = get_logger(__name__)

MAX_ROUTES_DETAIL = 50  # Max routes to include detailed schedule stats for
SAMPLE_STOPS = 100  # Number of stops to sample for Q&A
SAMPLE_TRANSFERS = 50  # Number of transfers to sample


def precompute_feed(feed_dir: Path) -> dict:
    """Compute full summary for one cleaned feed directory."""
    feed_id = feed_dir.name.replace("mdb-", "")

    # Load metadata from feed_stats.json (written by clean_feed.py)
    stats_path = feed_dir / "feed_stats.json"
    metadata = {}
    if stats_path.exists():
        with open(stats_path, encoding="utf-8") as f:
            metadata = json.load(f)

    summary: dict = {
        "feed_id": feed_id,
        "provider": metadata.get("provider", ""),
        "country_code": metadata.get("country_code", ""),
    }

    summary["agency"] = _summarize_agency(feed_dir)
    summary["route_summary"] = _summarize_routes(feed_dir)
    summary["stop_summary"] = _summarize_stops(feed_dir)

    # Compute per-route schedule stats (trip counts, first/last times)
    route_ids = [r["route_id"] for r in summary["route_summary"].get("routes", [])]
    schedule_stats = _compute_route_schedules(feed_dir, route_ids)

    # Merge schedule stats into route details
    for route in summary["route_summary"].get("routes", []):
        rid = route["route_id"]
        if rid in schedule_stats:
            route.update(schedule_stats[rid])

    # Build stop name lookup for transfers
    stops_lookup = {}
    if (feed_dir / "stops.parquet").exists():
        stops_df = pd.read_parquet(feed_dir / "stops.parquet", columns=["stop_id", "stop_name"])
        stops_lookup = dict(zip(stops_df["stop_id"], stops_df["stop_name"]))

    summary["transfer_summary"] = _summarize_transfers(feed_dir, stops_lookup)
    summary["calendar_summary"] = _summarize_calendar(feed_dir)
    summary["network_stats"] = _compute_network_stats(summary)

    return summary


def _summarize_agency(feed_dir: Path) -> list[dict]:
    """Read agency.parquet, return list of agency dicts."""
    path = feed_dir / "agency.parquet"
    if not path.exists():
        return []

    df = pd.read_parquet(path)
    cols = ["agency_id", "agency_name", "agency_url", "agency_timezone"]
    available = [c for c in cols if c in df.columns]
    records = df[available].fillna("").to_dict("records")
    return records


def _summarize_routes(feed_dir: Path) -> dict:
    """Read routes.parquet, return route summary with type counts."""
    path = feed_dir / "routes.parquet"
    if not path.exists():
        return {"total_routes": 0, "by_type": {}, "routes": []}

    df = pd.read_parquet(path)
    total = len(df)

    # Count by route_type
    by_type = {}
    if "route_type" in df.columns:
        type_counts = df["route_type"].dropna().value_counts()
        by_type = {int(k): int(v) for k, v in type_counts.items()}

    # Route details (limited to MAX_ROUTES_DETAIL)
    cols = ["route_id", "route_short_name", "route_long_name", "route_type", "agency_id"]
    available = [c for c in cols if c in df.columns]
    routes_df = df[available].head(MAX_ROUTES_DETAIL)
    routes = routes_df.fillna("").to_dict("records")

    # Convert route_type to int where possible
    for r in routes:
        if "route_type" in r and r["route_type"] != "":
            try:
                r["route_type"] = int(r["route_type"])
            except (ValueError, TypeError):
                pass

    return {"total_routes": total, "by_type": by_type, "routes": routes}


def _summarize_stops(feed_dir: Path) -> dict:
    """Read stops.parquet, return stop summary."""
    path = feed_dir / "stops.parquet"
    if not path.exists():
        return {"total_stops": 0, "stations": [], "sample_stops": []}

    df = pd.read_parquet(path)
    total = len(df)

    # Count by location_type
    by_location_type = {}
    if "location_type" in df.columns:
        lt_counts = df["location_type"].dropna().value_counts()
        by_location_type = {int(k): int(v) for k, v in lt_counts.items()}

    # Stations (location_type == 1)
    stations = []
    if "location_type" in df.columns:
        station_df = df[df["location_type"] == 1]
        cols = ["stop_id", "stop_name", "stop_lat", "stop_lon"]
        available = [c for c in cols if c in station_df.columns]
        stations = station_df[available].head(50).fillna("").to_dict("records")

    # Sample stops for Q&A
    sample_n = min(SAMPLE_STOPS, total)
    sample_df = df.sample(n=sample_n, random_state=42) if total > 0 else df
    cols = ["stop_id", "stop_name", "stop_lat", "stop_lon", "zone_id", "parent_station"]
    available = [c for c in cols if c in sample_df.columns]
    sample_stops = sample_df[available].fillna("").to_dict("records")

    return {
        "total_stops": total,
        "by_location_type": by_location_type,
        "stations": stations,
        "sample_stops": sample_stops,
    }


def _compute_route_schedules(feed_dir: Path, route_ids: list[str]) -> dict[str, dict]:
    """Compute per-route trip count, first/last departure, stop count.

    Uses row-group iteration on stop_times.parquet to avoid loading
    all rows into memory.
    """
    trips_path = feed_dir / "trips.parquet"
    st_path = feed_dir / "stop_times.parquet"

    if not trips_path.exists() or not st_path.exists():
        return {}

    # Build trip_id -> route_id mapping
    # Only request columns that exist in the file
    available_cols = pq.read_schema(trips_path).names
    trip_cols = ["trip_id", "route_id"]
    if "trip_headsign" in available_cols:
        trip_cols.append("trip_headsign")

    trips_df = pd.read_parquet(trips_path, columns=trip_cols)
    trip_to_route: dict[str, str] = {}
    trip_to_headsign: dict[str, str] = {}
    for _, row in trips_df.iterrows():
        tid = row["trip_id"]
        if pd.notna(tid) and pd.notna(row["route_id"]):
            trip_to_route[str(tid)] = str(row["route_id"])
        if pd.notna(tid) and pd.notna(row.get("trip_headsign")):
            trip_to_headsign[str(tid)] = str(row["trip_headsign"])

    # Initialize per-route accumulators
    route_set = set(route_ids)
    route_stats: dict[str, dict] = {
        rid: {"trip_ids": set(), "departures": [], "stop_ids": set(), "headsigns": set()}
        for rid in route_set
    }

    # Count trips per route from trips table directly (faster)
    trip_route_counts = trips_df["route_id"].value_counts()
    for rid in route_set:
        if rid in trip_route_counts.index:
            route_trips = trips_df[trips_df["route_id"] == rid]["trip_id"]
            route_stats[rid]["trip_ids"] = set(str(t) for t in route_trips if pd.notna(t))

    # Collect headsigns per route
    for tid, rid in trip_to_route.items():
        if rid in route_stats and tid in trip_to_headsign:
            route_stats[rid]["headsigns"].add(trip_to_headsign[tid])

    # Scan stop_times for first/last departures and stop counts
    pf = pq.ParquetFile(st_path)
    needed_cols = ["trip_id", "departure_time", "stop_id", "stop_sequence"]

    for rg_idx in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg_idx, columns=needed_cols)
        chunk = table.to_pandas()
        chunk["trip_id"] = chunk["trip_id"].astype(str)

        # Map to route
        chunk["route_id"] = chunk["trip_id"].map(trip_to_route)
        chunk = chunk.dropna(subset=["route_id"])

        # Collect stop_ids per route
        for route_id, group in chunk.groupby("route_id"):
            if route_id in route_stats:
                route_stats[route_id]["stop_ids"].update(
                    str(s) for s in group["stop_id"].dropna()
                )

        # First stop per trip (stop_sequence == min) for departure times
        if "stop_sequence" in chunk.columns:
            first_stops = chunk.loc[chunk.groupby("trip_id")["stop_sequence"].idxmin()]
        else:
            first_stops = chunk.drop_duplicates(subset=["trip_id"], keep="first")

        for route_id, group in first_stops.groupby("route_id"):
            if route_id in route_stats:
                deps = group["departure_time"].dropna().tolist()
                route_stats[route_id]["departures"].extend(str(d) for d in deps)

    # Finalize
    result = {}
    for rid, stats in route_stats.items():
        deps = sorted([d for d in stats["departures"] if d and d.strip()])
        result[rid] = {
            "trip_count": len(stats["trip_ids"]),
            "stop_count": len(stats["stop_ids"]),
            "first_departure": deps[0] if deps else None,
            "last_departure": deps[-1] if deps else None,
            "headsigns": sorted(stats["headsigns"])[:5],  # Top 5
        }

    return result


def _summarize_transfers(feed_dir: Path, stops_lookup: dict[str, str]) -> dict:
    """Read transfers.parquet, enrich with stop names."""
    path = feed_dir / "transfers.parquet"
    if not path.exists():
        return {"total_transfers": 0, "sample_transfers": []}

    df = pd.read_parquet(path)
    total = len(df)

    # Sample transfers
    sample_n = min(SAMPLE_TRANSFERS, total)
    sample_df = df.sample(n=sample_n, random_state=42) if total > 0 else df

    transfers = []
    for _, row in sample_df.iterrows():
        from_id = str(row.get("from_stop_id", ""))
        to_id = str(row.get("to_stop_id", ""))
        transfers.append({
            "from_stop_id": from_id,
            "from_stop_name": stops_lookup.get(from_id, ""),
            "to_stop_id": to_id,
            "to_stop_name": stops_lookup.get(to_id, ""),
            "transfer_type": int(row["transfer_type"]) if pd.notna(row.get("transfer_type")) else None,
            "min_transfer_time": int(row["min_transfer_time"]) if pd.notna(row.get("min_transfer_time")) else None,
        })

    return {"total_transfers": total, "sample_transfers": transfers}


def _summarize_calendar(feed_dir: Path) -> dict:
    """Read calendar.parquet for service date ranges and patterns."""
    result: dict = {"weekday_services": 0, "weekend_services": 0, "date_range": []}

    cal_path = feed_dir / "calendar.parquet"
    if cal_path.exists():
        df = pd.read_parquet(cal_path)
        if "monday" in df.columns:
            weekday_mask = (df["monday"] == 1) | (df["tuesday"] == 1) | (df["wednesday"] == 1) | (df["thursday"] == 1) | (df["friday"] == 1)
            result["weekday_services"] = int(weekday_mask.sum())
        if "saturday" in df.columns:
            weekend_mask = (df["saturday"] == 1) | (df["sunday"] == 1)
            result["weekend_services"] = int(weekend_mask.sum())
        if "start_date" in df.columns and "end_date" in df.columns:
            starts = df["start_date"].dropna()
            ends = df["end_date"].dropna()
            if len(starts) > 0 and len(ends) > 0:
                result["date_range"] = [str(starts.min()), str(ends.max())]

    # Also check calendar_dates
    cd_path = feed_dir / "calendar_dates.parquet"
    if cd_path.exists():
        df = pd.read_parquet(cd_path)
        result["calendar_dates_count"] = len(df)
        if "date" in df.columns:
            dates = df["date"].dropna()
            if len(dates) > 0:
                if not result["date_range"]:
                    result["date_range"] = [str(dates.min()), str(dates.max())]

    return result


def _compute_network_stats(summary: dict) -> dict:
    """Compute aggregate network statistics from the summary."""
    route_summary = summary.get("route_summary", {})
    stop_summary = summary.get("stop_summary", {})
    total_routes = route_summary.get("total_routes", 0)
    total_stops = stop_summary.get("total_stops", 0)

    routes = route_summary.get("routes", [])
    total_trips = sum(r.get("trip_count", 0) for r in routes)
    total_stop_times = 0  # Not available at this level

    avg_stops = total_stops / total_routes if total_routes > 0 else 0
    avg_trips = total_trips / total_routes if total_routes > 0 else 0

    return {
        "total_routes": total_routes,
        "total_stops": total_stops,
        "total_trips": total_trips,
        "avg_stops_per_route": round(avg_stops, 1),
        "avg_trips_per_route": round(avg_trips, 1),
    }


def precompute_all_feeds(
    cleaned_dir: Path | None = None,
    feed_ids: list[str] | None = None,
    force: bool = False,
) -> None:
    """Iterate all cleaned feeds and generate feed_summary.json."""
    cdir = cleaned_dir or CLEANED_DIR

    feed_dirs = sorted(
        d for d in cdir.iterdir()
        if d.is_dir() and d.name.startswith("mdb-")
    )

    if feed_ids:
        feed_dirs = [d for d in feed_dirs if d.name.replace("mdb-", "") in feed_ids]

    total = len(feed_dirs)
    logger.info("Pre-computing stats for %d feeds", total)

    for i, feed_dir in enumerate(feed_dirs, 1):
        feed_id = feed_dir.name.replace("mdb-", "")
        summary_path = feed_dir / "feed_summary.json"

        if summary_path.exists() and not force:
            logger.info("[%d/%d] mdb-%s: already computed, skipping", i, total, feed_id)
            continue

        logger.info("[%d/%d] mdb-%s: computing...", i, total, feed_id)
        summary = precompute_feed(feed_dir)

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        route_count = summary.get("route_summary", {}).get("total_routes", 0)
        stop_count = summary.get("stop_summary", {}).get("total_stops", 0)
        logger.info(
            "[%d/%d] mdb-%s: %s — %d routes, %d stops",
            i, total, feed_id, summary.get("provider", ""), route_count, stop_count,
        )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Pre-compute feed statistics")
    parser.add_argument("--feed-id", nargs="+", help="Specific feed ID(s)")
    parser.add_argument("--force", action="store_true", help="Re-compute existing stats")
    args = parser.parse_args()

    precompute_all_feeds(feed_ids=args.feed_id, force=args.force)


if __name__ == "__main__":
    main()
