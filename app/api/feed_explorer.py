"""GTFS Feed Explorer — in-memory feed processing and AI Q&A.

Processes uploaded GTFS ZIPs without writing to disk:
1. Validates ZIP structure
2. Reads CSVs into pandas DataFrames
3. Computes summary statistics
4. Answers questions using the model with feed context
"""

import csv
import io
import tempfile
import time
import uuid
import zipfile
from pathlib import Path

import pandas as pd

from scripts.config import get_logger
from scripts.validate_feed import validate_gtfs_zip, FeedValidationResult

logger = get_logger(__name__)

# Session store: {upload_id: {summary, created_at}}
_sessions: dict[str, dict] = {}
SESSION_TTL = 1800  # 30 minutes

# Limits
MAX_STOP_TIMES_ROWS = 500_000
MAX_ROUTES_DETAIL = 50
SAMPLE_STOPS = 50
SAMPLE_TRANSFERS = 30

ROUTE_TYPE_NAMES: dict[int, str] = {
    0: "Tram/Streetcar/Light rail",
    1: "Subway/Metro",
    2: "Rail/Commuter rail",
    3: "Bus",
    4: "Ferry",
    5: "Cable tram",
    6: "Aerial lift/Gondola",
    7: "Funicular",
    11: "Trolleybus",
    12: "Monorail",
}


# ── Session management ────────────────────────────────────────────────────────

def _cleanup_sessions() -> None:
    """Remove sessions older than SESSION_TTL."""
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v["created_at"] > SESSION_TTL]
    for k in expired:
        del _sessions[k]
        logger.info("Evicted session %s", k)


def store_session(summary: dict) -> str:
    """Store a feed summary and return the upload_id."""
    _cleanup_sessions()
    upload_id = uuid.uuid4().hex[:12]
    _sessions[upload_id] = {"summary": summary, "created_at": time.time()}
    return upload_id


def get_session(upload_id: str) -> dict | None:
    """Retrieve a stored feed summary."""
    session = _sessions.get(upload_id)
    if session is None:
        return None
    if time.time() - session["created_at"] > SESSION_TTL:
        del _sessions[upload_id]
        return None
    return session["summary"]


# ── CSV reading from ZIP ──────────────────────────────────────────────────────

def _find_in_zip(names: list[str], filename: str) -> str | None:
    """Find a file in the ZIP, handling nested directories."""
    for name in names:
        if Path(name).name == filename:
            return name
    return None


def _read_csv_from_zip(
    zf: zipfile.ZipFile,
    all_names: list[str],
    filename: str,
    max_rows: int | None = None,
) -> pd.DataFrame | None:
    """Read a CSV file from a ZIP into a DataFrame."""
    actual_path = _find_in_zip(all_names, filename)
    if actual_path is None:
        return None

    try:
        data = zf.read(actual_path)
        if len(data) == 0:
            return None

        text = data.decode("utf-8-sig")
        df = pd.read_csv(
            io.StringIO(text),
            dtype=str,
            keep_default_na=False,
            nrows=max_rows,
        )
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        logger.warning("Failed to read %s: %s", filename, e)
        return None


# ── Feed exploration ──────────────────────────────────────────────────────────

def explore_feed_from_zip(zip_bytes: bytes) -> tuple[dict, dict | None]:
    """Validate and explore a GTFS ZIP from raw bytes.

    Returns:
        (validation_dict, summary_dict or None if invalid)
    """
    # Write to temp file for validation (validate_gtfs_zip needs a Path)
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp_path = Path(tmp.name)

    try:
        validation = validate_gtfs_zip(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    validation_dict = {
        "is_valid": validation.is_valid,
        "errors": validation.errors,
        "warnings": validation.warnings,
        "file_count": validation.file_count,
        "files_found": validation.files_found,
        "total_size_bytes": validation.total_size_bytes,
    }

    if not validation.is_valid:
        return validation_dict, None

    # Read CSVs into DataFrames
    try:
        tables = _read_all_tables(zip_bytes)
    except Exception as e:
        logger.error("Failed to read GTFS tables: %s", e)
        validation_dict["warnings"].append(f"Could not parse feed data: {e}")
        return validation_dict, None

    # Compute summary
    summary = _build_summary(tables)
    return validation_dict, summary


def _read_all_tables(zip_bytes: bytes) -> dict[str, pd.DataFrame]:
    """Read all GTFS CSV files from ZIP bytes into DataFrames."""
    tables: dict[str, pd.DataFrame] = {}

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        all_names = zf.namelist()

        files_to_read = {
            "agency": ("agency.txt", None),
            "routes": ("routes.txt", None),
            "trips": ("trips.txt", None),
            "stops": ("stops.txt", None),
            "stop_times": ("stop_times.txt", MAX_STOP_TIMES_ROWS),
            "calendar": ("calendar.txt", None),
            "calendar_dates": ("calendar_dates.txt", None),
            "transfers": ("transfers.txt", None),
        }

        for key, (filename, max_rows) in files_to_read.items():
            df = _read_csv_from_zip(zf, all_names, filename, max_rows)
            if df is not None:
                tables[key] = df

    return tables


def _build_summary(tables: dict[str, pd.DataFrame]) -> dict:
    """Build a feed summary from in-memory DataFrames."""
    summary: dict = {}

    summary["agency"] = _summarize_agency(tables.get("agency"))
    summary["route_summary"] = _summarize_routes(tables.get("routes"))
    summary["stop_summary"] = _summarize_stops(tables.get("stops"))
    summary["calendar_summary"] = _summarize_calendar(
        tables.get("calendar"), tables.get("calendar_dates")
    )
    summary["transfer_summary"] = _summarize_transfers(
        tables.get("transfers"), tables.get("stops")
    )

    # Compute route schedules (trip counts, first/last departure)
    routes = summary["route_summary"].get("routes", [])
    route_ids = [r["route_id"] for r in routes]
    schedule_stats = _compute_route_schedules(
        tables.get("trips"), tables.get("stop_times"), route_ids
    )
    for route in routes:
        rid = route["route_id"]
        if rid in schedule_stats:
            route.update(schedule_stats[rid])

    summary["network_stats"] = _compute_network_stats(summary)
    return summary


# ── Summarization functions (adapted from precompute_feed_stats.py) ───────────

def _summarize_agency(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    cols = ["agency_id", "agency_name", "agency_url", "agency_timezone"]
    available = [c for c in cols if c in df.columns]
    return df[available].fillna("").to_dict("records")


def _summarize_routes(df: pd.DataFrame | None) -> dict:
    if df is None or df.empty:
        return {"total_routes": 0, "by_type": {}, "routes": []}

    total = len(df)

    by_type: dict[int, int] = {}
    if "route_type" in df.columns:
        for val, count in df["route_type"].value_counts().items():
            try:
                by_type[int(val)] = int(count)
            except (ValueError, TypeError):
                pass

    cols = ["route_id", "route_short_name", "route_long_name", "route_type"]
    available = [c for c in cols if c in df.columns]
    routes_df = df[available].head(MAX_ROUTES_DETAIL).fillna("")
    routes = routes_df.to_dict("records")

    for r in routes:
        if "route_type" in r and r["route_type"] != "":
            try:
                r["route_type"] = int(r["route_type"])
            except (ValueError, TypeError):
                pass

    return {"total_routes": total, "by_type": by_type, "routes": routes}


def _summarize_stops(df: pd.DataFrame | None) -> dict:
    if df is None or df.empty:
        return {"total_stops": 0, "by_location_type": {}, "sample_stops": []}

    total = len(df)

    by_location_type: dict[int, int] = {}
    if "location_type" in df.columns:
        for val, count in df["location_type"].value_counts().items():
            try:
                by_location_type[int(val)] = int(count)
            except (ValueError, TypeError):
                pass

    # Sample stops
    sample_n = min(SAMPLE_STOPS, total)
    sample_df = df.sample(n=sample_n, random_state=42) if total > 0 else df
    cols = ["stop_id", "stop_name", "stop_lat", "stop_lon"]
    available = [c for c in cols if c in sample_df.columns]
    sample_stops = sample_df[available].fillna("").to_dict("records")

    return {
        "total_stops": total,
        "by_location_type": by_location_type,
        "sample_stops": sample_stops,
    }


def _summarize_calendar(
    cal_df: pd.DataFrame | None,
    cal_dates_df: pd.DataFrame | None,
) -> dict:
    result: dict = {
        "weekday_services": 0,
        "weekend_services": 0,
        "date_range": [],
        "calendar_dates_count": 0,
    }

    if cal_df is not None and not cal_df.empty:
        day_cols = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        if all(c in cal_df.columns for c in day_cols):
            # Convert to numeric for comparison
            for c in day_cols + ["saturday", "sunday"]:
                if c in cal_df.columns:
                    cal_df[c] = pd.to_numeric(cal_df[c], errors="coerce").fillna(0)

            weekday_mask = cal_df[day_cols].max(axis=1) == 1
            result["weekday_services"] = int(weekday_mask.sum())

        weekend_cols = ["saturday", "sunday"]
        if all(c in cal_df.columns for c in weekend_cols):
            weekend_mask = cal_df[weekend_cols].max(axis=1) == 1
            result["weekend_services"] = int(weekend_mask.sum())

        if "start_date" in cal_df.columns and "end_date" in cal_df.columns:
            starts = cal_df["start_date"].dropna()
            ends = cal_df["end_date"].dropna()
            if len(starts) > 0 and len(ends) > 0:
                result["date_range"] = [str(starts.min()), str(ends.max())]

    if cal_dates_df is not None and not cal_dates_df.empty:
        result["calendar_dates_count"] = len(cal_dates_df)
        if "date" in cal_dates_df.columns and not result["date_range"]:
            dates = cal_dates_df["date"].dropna()
            if len(dates) > 0:
                result["date_range"] = [str(dates.min()), str(dates.max())]

    return result


def _summarize_transfers(
    transfers_df: pd.DataFrame | None,
    stops_df: pd.DataFrame | None,
) -> dict:
    if transfers_df is None or transfers_df.empty:
        return {"total_transfers": 0, "sample_transfers": []}

    total = len(transfers_df)

    # Build stop name lookup
    stops_lookup: dict[str, str] = {}
    if stops_df is not None and "stop_id" in stops_df.columns and "stop_name" in stops_df.columns:
        stops_lookup = dict(zip(stops_df["stop_id"], stops_df["stop_name"]))

    sample_n = min(SAMPLE_TRANSFERS, total)
    sample_df = transfers_df.sample(n=sample_n, random_state=42) if total > 0 else transfers_df

    transfers = []
    for _, row in sample_df.iterrows():
        from_id = str(row.get("from_stop_id", ""))
        to_id = str(row.get("to_stop_id", ""))
        transfers.append({
            "from_stop_name": stops_lookup.get(from_id, from_id),
            "to_stop_name": stops_lookup.get(to_id, to_id),
            "transfer_type": _safe_int(row.get("transfer_type")),
            "min_transfer_time": _safe_int(row.get("min_transfer_time")),
        })

    return {"total_transfers": total, "sample_transfers": transfers}


def _compute_route_schedules(
    trips_df: pd.DataFrame | None,
    stop_times_df: pd.DataFrame | None,
    route_ids: list[str],
) -> dict[str, dict]:
    """Compute per-route trip count, stop count, first/last departure."""
    if trips_df is None or stop_times_df is None:
        return {}

    if "trip_id" not in trips_df.columns or "route_id" not in trips_df.columns:
        return {}

    # Build trip_id -> route_id mapping
    trip_to_route = dict(zip(trips_df["trip_id"].astype(str), trips_df["route_id"].astype(str)))

    # Build trip_id -> headsign mapping
    trip_to_headsign: dict[str, str] = {}
    if "trip_headsign" in trips_df.columns:
        for _, row in trips_df.iterrows():
            tid = str(row["trip_id"])
            hs = row.get("trip_headsign", "")
            if hs and str(hs).strip():
                trip_to_headsign[tid] = str(hs)

    route_set = set(route_ids)
    route_stats: dict[str, dict] = {
        rid: {"trip_ids": set(), "departures": [], "stop_ids": set(), "headsigns": set()}
        for rid in route_set
    }

    # Count trips per route
    for _, row in trips_df.iterrows():
        rid = str(row["route_id"])
        tid = str(row["trip_id"])
        if rid in route_stats:
            route_stats[rid]["trip_ids"].add(tid)
            if tid in trip_to_headsign:
                route_stats[rid]["headsigns"].add(trip_to_headsign[tid])

    # Scan stop_times for departures and stop counts
    if "trip_id" in stop_times_df.columns:
        st = stop_times_df.copy()
        st["trip_id"] = st["trip_id"].astype(str)
        st["route_id"] = st["trip_id"].map(trip_to_route)
        st = st.dropna(subset=["route_id"])

        # Collect stop_ids per route
        if "stop_id" in st.columns:
            for route_id, group in st.groupby("route_id"):
                if route_id in route_stats:
                    route_stats[route_id]["stop_ids"].update(
                        str(s) for s in group["stop_id"].dropna()
                    )

        # First departure per trip
        if "departure_time" in st.columns:
            if "stop_sequence" in st.columns:
                st["stop_sequence"] = pd.to_numeric(st["stop_sequence"], errors="coerce")
                first_stops = st.loc[st.groupby("trip_id")["stop_sequence"].idxmin()]
            else:
                first_stops = st.drop_duplicates(subset=["trip_id"], keep="first")

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
            "headsigns": sorted(stats["headsigns"])[:5],
        }

    return result


def _compute_network_stats(summary: dict) -> dict:
    route_summary = summary.get("route_summary", {})
    stop_summary = summary.get("stop_summary", {})
    total_routes = route_summary.get("total_routes", 0)
    total_stops = stop_summary.get("total_stops", 0)

    routes = route_summary.get("routes", [])
    total_trips = sum(r.get("trip_count", 0) for r in routes)

    avg_stops = total_stops / total_routes if total_routes > 0 else 0
    avg_trips = total_trips / total_routes if total_routes > 0 else 0

    return {
        "total_routes": total_routes,
        "total_stops": total_stops,
        "total_trips": total_trips,
        "avg_stops_per_route": round(avg_stops, 1),
        "avg_trips_per_route": round(avg_trips, 1),
    }


def _safe_int(val) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


# ── AI Q&A about a feed ───────────────────────────────────────────────────────

def build_feed_context(summary: dict) -> str:
    """Build a context string from feed summary for the model prompt."""
    parts = []

    # Agency info
    agencies = summary.get("agency", [])
    if agencies:
        a = agencies[0]
        parts.append(f"Agency: {a.get('agency_name', 'Unknown')} (timezone: {a.get('agency_timezone', 'unknown')})")

    # Route summary
    rs = summary.get("route_summary", {})
    parts.append(f"Total routes: {rs.get('total_routes', 0)}")
    by_type = rs.get("by_type", {})
    if by_type:
        type_parts = [f"{count} {ROUTE_TYPE_NAMES.get(int(rt), f'type {rt}')}" for rt, count in sorted(by_type.items())]
        parts.append(f"Route types: {', '.join(type_parts)}")

    # Top routes
    routes = rs.get("routes", [])[:20]
    if routes:
        route_lines = []
        for r in routes:
            name = r.get("route_short_name") or r.get("route_long_name", "?")
            rt = ROUTE_TYPE_NAMES.get(r.get("route_type", -1), "unknown")
            trips = r.get("trip_count", 0)
            stops = r.get("stop_count", 0)
            first = r.get("first_departure", "")
            last = r.get("last_departure", "")
            route_lines.append(f"  Route {name}: {rt}, {trips} trips, {stops} stops, {first}-{last}")
        parts.append("Route details:\n" + "\n".join(route_lines))

    # Stops
    ss = summary.get("stop_summary", {})
    parts.append(f"Total stops: {ss.get('total_stops', 0)}")

    # Calendar
    cs = summary.get("calendar_summary", {})
    parts.append(f"Weekday services: {cs.get('weekday_services', 0)}, Weekend services: {cs.get('weekend_services', 0)}")
    dr = cs.get("date_range", [])
    if dr:
        parts.append(f"Service date range: {dr[0]} to {dr[1]}")

    # Transfers
    ts = summary.get("transfer_summary", {})
    parts.append(f"Transfer connections: {ts.get('total_transfers', 0)}")

    # Network stats
    ns = summary.get("network_stats", {})
    parts.append(f"Network: {ns.get('total_trips', 0)} total trips, avg {ns.get('avg_stops_per_route', 0)} stops/route, avg {ns.get('avg_trips_per_route', 0)} trips/route")

    return "\n".join(parts)


def build_feed_prompt(question: str, summary: dict) -> str:
    """Build a prompt that includes feed context for the model."""
    context = build_feed_context(summary)
    return (
        f"I have uploaded a GTFS feed. Here is the feed data:\n\n"
        f"{context}\n\n"
        f"Based on this feed data, answer the following question:\n{question}"
    )
