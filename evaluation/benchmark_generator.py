"""Benchmark generator for UmarTransit evaluation.

Generates 100-500 structured evaluation questions across 6 categories:
1. GTFS Terminology    - What GTFS concepts mean
2. GTFS Validation     - What makes a feed valid/invalid
3. Route Analysis      - Questions about specific routes from feed data
4. Journey Planning    - Multi-step transit reasoning
5. Schedule Reasoning  - Time/frequency/calendar logic
6. Transit Operations  - Real-world operational understanding

Each benchmark item includes:
- question, expected_answer, scoring_criteria, difficulty, category

The generator uses:
- Feed summaries (from datasets/cleaned/*/feed_summary.json)
- GTFS specification knowledge (hardcoded)
- Synthetic reasoning scenarios
"""

import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEANED_DIR = PROJECT_ROOT / "datasets" / "cleaned"
BENCHMARK_PATH = Path(__file__).resolve().parent / "benchmark.json"

# Seed for reproducibility
random.seed(42)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

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


def _rt_name(rt: int) -> str:
    return ROUTE_TYPE_NAMES.get(rt, f"Unknown (type {rt})")


def _format_time(t: str | None) -> str:
    if not t:
        return "unknown"
    parts = t.split(":")
    if len(parts) != 3:
        return t
    hour = int(parts[0])
    minute = parts[1]
    if hour >= 24:
        real_hour = hour - 24
        period = "AM" if real_hour < 12 else "PM"
        display = real_hour if real_hour != 0 else 12
        if display > 12:
            display -= 12
        return f"{display}:{minute} {period} (next day)"
    period = "AM" if hour < 12 else "PM"
    display = hour if hour != 0 else 12
    if display > 12:
        display -= 12
    return f"{display}:{minute} {period}"


def load_feed_summaries() -> list[dict]:
    """Load all feed_summary.json files."""
    summaries = []
    for feed_dir in sorted(CLEANED_DIR.iterdir()):
        summary_path = feed_dir / "feed_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summaries.append(json.load(f))
    return summaries


# ═══════════════════════════════════════════════════════════════════════════════
# Category 1: GTFS Terminology (hardcoded knowledge questions)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_gtfs_terminology() -> list[dict]:
    """GTFS spec knowledge that any transit AI should know."""
    items = [
        {
            "question": "What is GTFS and what does the acronym stand for?",
            "expected_answer": "GTFS stands for General Transit Feed Specification. It is an open standard for sharing public transit schedule, route, and stop information using CSV files packaged in a ZIP archive.",
            "scoring_criteria": "Must mention: General Transit Feed Specification, open standard, CSV/ZIP format",
            "difficulty": "easy",
        },
        {
            "question": "What is the difference between GTFS Static and GTFS Realtime?",
            "expected_answer": "GTFS Static contains scheduled/planned transit data (routes, stops, timetables) in CSV files. GTFS Realtime provides live data including vehicle positions, trip updates (delays), and service alerts using Protocol Buffers.",
            "scoring_criteria": "Must distinguish: Static = scheduled data in CSV, Realtime = live data (positions, delays, alerts) in Protocol Buffers",
            "difficulty": "easy",
        },
        {
            "question": "What are the required files in a GTFS Static feed?",
            "expected_answer": "Required files: agency.txt, routes.txt, trips.txt, stops.txt, stop_times.txt, and at least one of calendar.txt or calendar_dates.txt.",
            "scoring_criteria": "Must list all 5 core files (agency, routes, trips, stops, stop_times) and mention calendar/calendar_dates requirement",
            "difficulty": "medium",
        },
        {
            "question": "What does route_type 0 represent in GTFS?",
            "expected_answer": "Route_type 0 represents Tram, Streetcar, or Light rail service — any light rail or street-level transit system within a metropolitan area.",
            "scoring_criteria": "Must mention tram/streetcar/light rail",
            "difficulty": "easy",
        },
        {
            "question": "What does route_type 1 represent in GTFS?",
            "expected_answer": "Route_type 1 represents Subway or Metro service — any underground rail system within a metropolitan area.",
            "scoring_criteria": "Must mention subway or metro",
            "difficulty": "easy",
        },
        {
            "question": "What does route_type 3 represent in GTFS?",
            "expected_answer": "Route_type 3 represents Bus service. It is the most common route type in GTFS feeds.",
            "scoring_criteria": "Must mention bus",
            "difficulty": "easy",
        },
        {
            "question": "Explain the relationship between routes.txt, trips.txt, and stop_times.txt in GTFS.",
            "expected_answer": "Routes contain multiple trips (linked by route_id). Each trip has multiple stop_times (linked by trip_id). A route is a group of trips shown as a single service. A trip is one journey at a specific time. Stop_times list arrival/departure at each stop along a trip.",
            "scoring_criteria": "Must explain the hierarchy: routes → trips → stop_times, and the linking fields (route_id, trip_id)",
            "difficulty": "medium",
        },
        {
            "question": "What is the purpose of shapes.txt in GTFS?",
            "expected_answer": "shapes.txt defines the physical geographic path a vehicle follows along a route. It contains sequences of latitude/longitude points. Trips reference shapes via shape_id to draw route lines on maps.",
            "scoring_criteria": "Must mention: geographic path, lat/lon points, map visualization",
            "difficulty": "medium",
        },
        {
            "question": "What is the difference between calendar.txt and calendar_dates.txt?",
            "expected_answer": "calendar.txt defines regular weekly service patterns (day-of-week flags with date ranges). calendar_dates.txt defines exceptions — adding service on specific dates (exception_type=1) or removing service (exception_type=2). calendar_dates overrides calendar for specific dates.",
            "scoring_criteria": "Must explain: calendar = regular patterns, calendar_dates = exceptions, exception_type values",
            "difficulty": "medium",
        },
        {
            "question": "What does the location_type field in stops.txt indicate?",
            "expected_answer": "location_type indicates: 0 or blank = stop/platform, 1 = station (parent), 2 = entrance/exit, 3 = generic node, 4 = boarding area. Stations group related stops via parent_station.",
            "scoring_criteria": "Must list at least types 0, 1, 2 and explain parent_station grouping",
            "difficulty": "medium",
        },
        {
            "question": "Can departure times in GTFS stop_times.txt exceed 24:00:00? Why?",
            "expected_answer": "Yes. Times greater than 24:00:00 represent trips extending past midnight relative to the service day. For example, 25:30:00 means 1:30 AM the next day. This avoids ambiguity about which calendar day a late-night trip belongs to.",
            "scoring_criteria": "Must confirm yes, explain midnight-crossing convention, give example",
            "difficulty": "medium",
        },
        {
            "question": "What are the four transfer types defined in GTFS transfers.txt?",
            "expected_answer": "Type 0: recommended transfer point. Type 1: timed transfer (vehicle waits). Type 2: minimum time required (min_transfer_time). Type 3: no transfer possible between the stops.",
            "scoring_criteria": "Must list all 4 types with descriptions",
            "difficulty": "medium",
        },
        {
            "question": "What is frequencies.txt used for in GTFS?",
            "expected_answer": "frequencies.txt defines headway-based service for routes that run at regular intervals rather than fixed schedules. It specifies start_time, end_time, and headway_secs. The exact_times field indicates exact (1) or approximate (0) timing.",
            "scoring_criteria": "Must mention headway-based service, start/end times, headway_secs",
            "difficulty": "medium",
        },
        {
            "question": "What does the direction_id field mean in GTFS trips.txt?",
            "expected_answer": "direction_id distinguishes between two directions of travel on a route using values 0 and 1 (e.g., outbound vs inbound, northbound vs southbound). It is optional and agency-defined.",
            "scoring_criteria": "Must mention: values 0/1, bidirectional, agency-defined meaning",
            "difficulty": "easy",
        },
        {
            "question": "How is wheelchair accessibility represented in GTFS?",
            "expected_answer": "In trips.txt, wheelchair_accessible indicates if the vehicle accommodates wheelchairs (0=no info, 1=yes, 2=no). In stops.txt, wheelchair_boarding indicates if boarding is possible (0=no info, 1=some accessible, 2=not possible).",
            "scoring_criteria": "Must mention both trips.txt and stops.txt fields with their values",
            "difficulty": "medium",
        },
        {
            "question": "What information does feed_info.txt contain?",
            "expected_answer": "feed_info.txt provides metadata: feed_publisher_name, feed_publisher_url, feed_lang (language), feed_start_date, feed_end_date (validity period), and feed_version.",
            "scoring_criteria": "Must mention publisher info, language, and validity dates",
            "difficulty": "easy",
        },
        {
            "question": "What is zone_id in GTFS stops.txt used for?",
            "expected_answer": "zone_id defines the fare zone for a stop. It works with fare_rules.txt to calculate zone-based fares where prices vary based on origin/destination zones.",
            "scoring_criteria": "Must mention fare zones and zone-based pricing",
            "difficulty": "easy",
        },
        {
            "question": "What is the stop_sequence field in stop_times.txt?",
            "expected_answer": "stop_sequence defines the order in which stops are visited during a trip. It must increase along the trip but does not need to be consecutive. It determines the sequence of arrivals and departures.",
            "scoring_criteria": "Must explain ordering of stops within a trip",
            "difficulty": "easy",
        },
        {
            "question": "What is a block_id in GTFS trips.txt?",
            "expected_answer": "block_id groups trips that a single vehicle operates sequentially. When consecutive trips share the same block_id, a passenger can stay on the vehicle for a seat transfer without getting off. It represents a vehicle's work assignment.",
            "scoring_criteria": "Must explain: vehicle continuity, sequential trips by same vehicle",
            "difficulty": "hard",
        },
        {
            "question": "What is the purpose of the parent_station field in stops.txt?",
            "expected_answer": "parent_station links a child stop (platform, entrance, boarding area) to its parent station. A station (location_type=1) groups related stops. For example, a subway station may have multiple platforms, each as a separate stop record pointing to the same parent_station.",
            "scoring_criteria": "Must explain hierarchical grouping of stops under a station",
            "difficulty": "medium",
        },
        {
            "question": "What is fare_attributes.txt in GTFS?",
            "expected_answer": "fare_attributes.txt defines fare classes with price, currency, payment method (on board or before), and transfer rules (number of transfers allowed, transfer duration). It works with fare_rules.txt to map fares to routes and zones.",
            "scoring_criteria": "Must mention price, currency, transfer rules",
            "difficulty": "medium",
        },
        {
            "question": "What is the timepoint field in stop_times.txt?",
            "expected_answer": "The timepoint field indicates whether arrival/departure times are exact (1) or approximate (0/empty). Exact timepoints are stops where the vehicle strictly adheres to the schedule. Approximate times are interpolated between timepoints.",
            "scoring_criteria": "Must distinguish exact vs approximate times",
            "difficulty": "hard",
        },
        {
            "question": "What is pathways.txt in GTFS?",
            "expected_answer": "pathways.txt describes physical pathways within stations connecting platforms, entrances, and other nodes. It includes pathway type (walkway, stairs, escalator, elevator), traversal time, and length. It enables indoor navigation and accessibility routing.",
            "scoring_criteria": "Must mention: station pathways, pathway types, accessibility/navigation",
            "difficulty": "hard",
        },
        {
            "question": "What does pickup_type and drop_off_type mean in stop_times.txt?",
            "expected_answer": "pickup_type indicates how passengers board: 0=regular, 1=no pickup, 2=phone agency to arrange, 3=coordinate with driver. drop_off_type works the same for alighting. These handle flag stops and request-only service.",
            "scoring_criteria": "Must list values 0-3 for at least one field",
            "difficulty": "hard",
        },
        {
            "question": "What is continuous_pickup and continuous_drop_off in GTFS?",
            "expected_answer": "These fields in routes.txt or stop_times.txt indicate whether riders can board or alight anywhere along a route segment, not just at stops. Values: 0=continuous service, 1=no continuous (default), 2=phone to arrange, 3=coordinate with driver. This models flex routes and flag-stop service.",
            "scoring_criteria": "Must explain: boarding/alighting anywhere along route, flex service",
            "difficulty": "hard",
        },
    ]
    for item in items:
        item["category"] = "gtfs_terminology"
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Category 2: GTFS Validation (what makes a feed correct/incorrect)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_gtfs_validation() -> list[dict]:
    """Questions about GTFS feed validation rules."""
    items = [
        {
            "question": "A GTFS feed contains routes.txt, trips.txt, stops.txt, and stop_times.txt but is missing agency.txt. Is this feed valid?",
            "expected_answer": "No, the feed is invalid. agency.txt is a required file in GTFS. It must be present to provide transit agency information including agency_name, agency_url, and agency_timezone.",
            "scoring_criteria": "Must state invalid and identify agency.txt as required",
            "difficulty": "easy",
        },
        {
            "question": "A GTFS feed has neither calendar.txt nor calendar_dates.txt. Is this valid?",
            "expected_answer": "No, this is invalid. A GTFS feed must include at least one of calendar.txt or calendar_dates.txt to define when service operates. Without either file, there is no way to determine service days.",
            "scoring_criteria": "Must state invalid and explain at least one is required",
            "difficulty": "easy",
        },
        {
            "question": "A trip in stop_times.txt has departure_time 08:00:00 at stop_sequence 1, but arrival_time 07:50:00 at stop_sequence 2. Is this valid?",
            "expected_answer": "No, this is invalid. Times must be non-decreasing along a trip. An arrival at stop_sequence 2 cannot be earlier than the departure from stop_sequence 1. This would mean the vehicle arrived before it departed.",
            "scoring_criteria": "Must identify the time ordering violation",
            "difficulty": "medium",
        },
        {
            "question": "A GTFS feed has a route in routes.txt with route_type value 99. Is this valid according to the spec?",
            "expected_answer": "It depends on the GTFS version. The base GTFS spec defines route_types 0-7 and 11-12. Route_type 99 is not standard. However, some extended route type schemes (like the Google Transit extensions) allow additional codes. Most validators would flag this as a warning or error.",
            "scoring_criteria": "Must note that 99 is not in the standard range (0-7, 11-12) and mention extended types",
            "difficulty": "medium",
        },
        {
            "question": "A trip references a service_id that does not appear in calendar.txt or calendar_dates.txt. What is the problem?",
            "expected_answer": "This is a referential integrity error. Every service_id referenced in trips.txt must exist in either calendar.txt or calendar_dates.txt. Without a matching service_id, the trip has no defined operating days and cannot be scheduled.",
            "scoring_criteria": "Must identify referential integrity issue and explain the consequence",
            "difficulty": "medium",
        },
        {
            "question": "A stop in stops.txt has stop_lat=0.0 and stop_lon=0.0. Is this a valid GTFS entry?",
            "expected_answer": "Technically the format is valid, but this is almost certainly an error. Coordinates (0,0) place the stop in the Gulf of Guinea off the coast of Africa (known as 'Null Island'). Validators flag this as a likely data quality issue since no transit stops exist at that location.",
            "scoring_criteria": "Must identify as likely error, mention Null Island or coordinates being in the ocean",
            "difficulty": "medium",
        },
        {
            "question": "A stop_times.txt entry has an empty arrival_time and departure_time. When is this acceptable in GTFS?",
            "expected_answer": "Empty times are acceptable for intermediate stops (not the first or last stop of a trip). The GTFS spec allows interpolation of times between timepoints. However, the first and last stop_times in a trip must have explicit times.",
            "scoring_criteria": "Must mention: allowed for intermediate stops, not for first/last, interpolation",
            "difficulty": "hard",
        },
        {
            "question": "What happens if two stops in stops.txt have the same stop_id?",
            "expected_answer": "This is invalid. stop_id must be unique within stops.txt. Duplicate stop_ids would cause ambiguity in stop_times.txt and transfers.txt references. Validators will reject the feed or flag it as a critical error.",
            "scoring_criteria": "Must state stop_id must be unique",
            "difficulty": "easy",
        },
        {
            "question": "A route has trips defined in trips.txt but none of those trips have entries in stop_times.txt. Is this valid?",
            "expected_answer": "No, this is invalid. Every trip must have at least two stop_time entries to define a meaningful journey (an origin and a destination). A trip without stop_times cannot be used for routing or scheduling.",
            "scoring_criteria": "Must state invalid and mention minimum of 2 stop_times needed",
            "difficulty": "medium",
        },
        {
            "question": "Can a GTFS feed have shapes.txt but no shape_id references in trips.txt?",
            "expected_answer": "Yes, this is technically valid since shapes.txt is optional. However, having shapes without referencing them in trips is wasteful — the shape data exists but is unused. Validators may flag this as a warning.",
            "scoring_criteria": "Must state valid but pointless/wasteful",
            "difficulty": "medium",
        },
        {
            "question": "A feed has calendar.txt with start_date=20250101 and end_date=20241231. What is wrong?",
            "expected_answer": "The end_date (2024-12-31) is before the start_date (2025-01-01), making the date range invalid. No service days would be active. The end_date must be equal to or later than start_date.",
            "scoring_criteria": "Must identify that end_date is before start_date",
            "difficulty": "easy",
        },
        {
            "question": "A trip has stop_sequence values 1, 2, 2, 3 in stop_times.txt. Is this valid?",
            "expected_answer": "No, this is invalid. stop_sequence values must be non-negative integers that increase along the trip. Having two entries with stop_sequence=2 creates ambiguity in the stop ordering. Each stop_time in a trip must have a unique stop_sequence.",
            "scoring_criteria": "Must identify duplicate stop_sequence as invalid",
            "difficulty": "medium",
        },
        {
            "question": "What validation issue exists if a route in routes.txt has an empty route_short_name AND an empty route_long_name?",
            "expected_answer": "This is a validation error. The GTFS spec requires that at least one of route_short_name or route_long_name must be provided. Both being empty means riders have no way to identify the route.",
            "scoring_criteria": "Must state at least one name is required",
            "difficulty": "medium",
        },
        {
            "question": "A GTFS feed has stops located in New York but the agency_timezone is set to 'Europe/London'. What kind of validation issue is this?",
            "expected_answer": "This is a data quality issue — the timezone does not match the geographic location of the stops. While technically valid format-wise, the incorrect timezone would cause all schedule times to be wrong for riders. Validators flag this as a geographic consistency warning.",
            "scoring_criteria": "Must identify timezone-geography mismatch",
            "difficulty": "medium",
        },
        {
            "question": "What happens if transfers.txt specifies transfer_type=2 but min_transfer_time is missing?",
            "expected_answer": "This is a validation issue. transfer_type=2 means a minimum transfer time is required, so the min_transfer_time field should be provided. Without it, the transfer time constraint cannot be enforced. Validators would flag this as an error or warning.",
            "scoring_criteria": "Must explain that type 2 requires min_transfer_time",
            "difficulty": "hard",
        },
        {
            "question": "A GTFS feed has a trip where stop_times go from stop A (departure 10:00) to stop B (arrival 10:00) — same time, different stops. Is this valid?",
            "expected_answer": "Yes, this is technically valid. GTFS allows equal arrival/departure times at consecutive stops, which can represent very short segments or time-rounding. However, it implies zero travel time between stops, which may be flagged as a warning by some validators.",
            "scoring_criteria": "Must state valid but potentially flagged as warning",
            "difficulty": "hard",
        },
        {
            "question": "Can a stop in stops.txt exist without being referenced in any stop_times.txt entry?",
            "expected_answer": "Yes, this is valid. stops.txt may contain parent stations (location_type=1), entrances (type 2), or generic nodes (type 3) that are not directly referenced in stop_times.txt. Even unused stop/platform records are technically valid but may indicate orphaned data.",
            "scoring_criteria": "Must state valid and mention parent stations or non-platform location types",
            "difficulty": "medium",
        },
        {
            "question": "What is wrong with a GTFS feed where all trips have the same service_id but calendar.txt shows that service runs on no days (monday=0 through sunday=0)?",
            "expected_answer": "If all day-of-week flags are 0 and there are no additions in calendar_dates.txt, then no trips would ever run. The feed is technically valid but operationally useless — it defines routes and trips that never operate.",
            "scoring_criteria": "Must identify that no service days = no active trips",
            "difficulty": "hard",
        },
    ]
    for item in items:
        item["category"] = "gtfs_validation"
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Category 3: Route Analysis (from real feed data)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_route_analysis(summaries: list[dict]) -> list[dict]:
    """Generate route analysis questions from feed data."""
    items: list[dict] = []

    for s in summaries:
        provider = s.get("provider", "")
        routes = s.get("route_summary", {}).get("routes", [])
        by_type = s.get("route_summary", {}).get("by_type", {})
        total_routes = s.get("route_summary", {}).get("total_routes", 0)

        if not routes or not provider:
            continue

        # Q: How many routes does agency X have?
        items.append({
            "question": f"How many transit routes does {provider} operate?",
            "expected_answer": f"{provider} operates {total_routes} routes.",
            "scoring_criteria": f"Must state {total_routes} routes",
            "difficulty": "easy",
            "category": "route_analysis",
        })

        # Q: What transit modes does agency X provide?
        if by_type:
            modes = ", ".join(
                f"{count} {_rt_name(int(rt))}" for rt, count in sorted(by_type.items())
            )
            items.append({
                "question": f"What types of transit services does {provider} offer?",
                "expected_answer": f"{provider} offers: {modes}.",
                "scoring_criteria": f"Must mention the transit modes and approximate counts",
                "difficulty": "easy",
                "category": "route_analysis",
            })

        # Q: Describe a specific route
        sample_routes = [r for r in routes if r.get("route_short_name")]
        if sample_routes:
            route = random.choice(sample_routes[:20])
            name = route["route_short_name"]
            rt = route.get("route_type", 3)
            trips = route.get("trip_count", 0)
            stops = route.get("stop_count", 0)
            items.append({
                "question": f"Describe route {name} operated by {provider}.",
                "expected_answer": f"Route {name} is a {_rt_name(int(rt))} service by {provider} with approximately {trips:,} trips serving {stops} stops.",
                "scoring_criteria": f"Must mention route type ({_rt_name(int(rt))}), trip count (~{trips}), and stop count (~{stops})",
                "difficulty": "medium",
                "category": "route_analysis",
            })

        # Q: Which route has the most trips?
        if len(routes) > 1:
            busiest = max(routes, key=lambda r: r.get("trip_count", 0))
            b_name = busiest.get("route_short_name") or busiest.get("route_long_name", "unknown")
            b_trips = busiest.get("trip_count", 0)
            items.append({
                "question": f"Which route in the {provider} network has the most scheduled trips?",
                "expected_answer": f"Route {b_name} has the most trips with approximately {b_trips:,} scheduled trips.",
                "scoring_criteria": f"Must identify route {b_name} with ~{b_trips} trips",
                "difficulty": "medium",
                "category": "route_analysis",
            })

        # Q: Which route serves the most stops?
        if len(routes) > 1:
            most_stops = max(routes, key=lambda r: r.get("stop_count", 0))
            ms_name = most_stops.get("route_short_name") or most_stops.get("route_long_name", "unknown")
            ms_stops = most_stops.get("stop_count", 0)
            items.append({
                "question": f"Which route in the {provider} network serves the most stops?",
                "expected_answer": f"Route {ms_name} serves the most stops with {ms_stops} stops.",
                "scoring_criteria": f"Must identify route {ms_name} with {ms_stops} stops",
                "difficulty": "medium",
                "category": "route_analysis",
            })

    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Category 4: Journey Planning (reasoning questions)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_journey_planning() -> list[dict]:
    """Transit reasoning and journey planning knowledge questions."""
    items = [
        {
            "question": "What factors should a journey planner consider when calculating the fastest route?",
            "expected_answer": "A journey planner should consider: scheduled departure/arrival times, transfer times between routes, walking distances to/from stops, real-time delays, service frequency, number of transfers, and time of day (peak vs off-peak schedules).",
            "scoring_criteria": "Must mention at least 4 of: times, transfers, walking, frequency, delays",
            "difficulty": "medium",
        },
        {
            "question": "A passenger needs to travel from stop A to stop C, but there is no direct route. Route 1 goes from A to B, and Route 2 goes from B to C. The transfer at B requires a minimum of 5 minutes. Route 1 arrives at B at 10:15 and Route 2 departs B at 10:18. Can the passenger make this connection?",
            "expected_answer": "No, the passenger cannot make this connection. The available transfer time is only 3 minutes (10:18 - 10:15), but the minimum transfer time is 5 minutes. The passenger would need to wait for a later Route 2 departure.",
            "scoring_criteria": "Must calculate 3 minutes available vs 5 required, conclude not possible",
            "difficulty": "medium",
        },
        {
            "question": "What is a timed transfer in public transit and how does GTFS represent it?",
            "expected_answer": "A timed transfer is when a departing vehicle waits for an arriving vehicle at a transfer point, ensuring passengers can make the connection. In GTFS, this is represented in transfers.txt with transfer_type=1, which means the departing trip is expected to wait for the arriving trip.",
            "scoring_criteria": "Must explain vehicle-waiting concept and mention transfer_type=1",
            "difficulty": "medium",
        },
        {
            "question": "Why might a journey planner suggest a route with more transfers but less total travel time over a direct route?",
            "expected_answer": "A route with transfers might be faster if the connecting services are more frequent, operate on express/rapid routes with fewer stops, or avoid congested areas. The total journey time includes waiting, riding, and transferring — a well-timed multi-transfer route can beat a slow direct route.",
            "scoring_criteria": "Must explain that total time matters more than transfer count",
            "difficulty": "medium",
        },
        {
            "question": "How does a transit planner handle trips that cross midnight in GTFS?",
            "expected_answer": "GTFS uses times greater than 24:00:00 for trips crossing midnight. For example, a trip departing at 23:45 and arriving at 00:15 would have times 23:45:00 and 24:15:00. This keeps all times on the same service day, avoiding date boundary confusion. The journey planner must convert these for display (24:15 → 12:15 AM next day).",
            "scoring_criteria": "Must explain times > 24:00:00 convention and service day concept",
            "difficulty": "hard",
        },
        {
            "question": "What is a fare zone and how does it affect journey planning?",
            "expected_answer": "A fare zone is a geographic area used for pricing. Fares may increase when crossing zone boundaries. Journey planners need zone information to calculate accurate fares, show users the cost of different route options, and help passengers choose the most economical path.",
            "scoring_criteria": "Must explain zone-based pricing and impact on route cost",
            "difficulty": "easy",
        },
        {
            "question": "A bus route runs every 10 minutes from 6:00 AM to 10:00 PM. How would this be represented in GTFS?",
            "expected_answer": "This can be represented using frequencies.txt with: trip_id referencing a template trip, start_time=06:00:00, end_time=22:00:00, headway_secs=600 (10 minutes × 60 seconds). Alternatively, each individual trip could be listed in stop_times.txt, but frequencies.txt is more efficient for regular-interval service.",
            "scoring_criteria": "Must mention frequencies.txt and headway_secs=600",
            "difficulty": "medium",
        },
        {
            "question": "What accessibility information should a journey planner use from GTFS?",
            "expected_answer": "A journey planner should use: wheelchair_accessible from trips.txt (vehicle accessibility), wheelchair_boarding from stops.txt (stop accessibility), and pathways.txt (station navigation for mobility-impaired riders). This ensures routes suggested to wheelchair users only include accessible vehicles, stops, and transfer paths.",
            "scoring_criteria": "Must mention wheelchair fields in both trips.txt and stops.txt",
            "difficulty": "medium",
        },
        {
            "question": "How does a journey planner determine if a transit service is running on a specific date?",
            "expected_answer": "It checks: 1) calendar.txt for the regular schedule — is the service_id active on that day of week and within the date range? 2) calendar_dates.txt for exceptions — is service added (exception_type=1) or removed (exception_type=2) on that date? Exceptions override the regular schedule.",
            "scoring_criteria": "Must explain checking both calendar.txt and calendar_dates.txt, with exceptions overriding",
            "difficulty": "medium",
        },
        {
            "question": "What is the difference between a guaranteed connection and a regular transfer?",
            "expected_answer": "A guaranteed (timed) connection means the departing vehicle will wait for the arriving vehicle, ensuring the transfer. A regular transfer has no such guarantee — if the arriving service is late, the passenger may miss the connection. In GTFS, transfer_type=1 represents guaranteed connections, while type=0 is recommended but not guaranteed.",
            "scoring_criteria": "Must distinguish guaranteed vs regular, mention transfer_type values",
            "difficulty": "medium",
        },
    ]
    for item in items:
        item["category"] = "journey_planning"
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Category 5: Schedule Reasoning (from real feed data + logic)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_schedule_reasoning(summaries: list[dict]) -> list[dict]:
    """Schedule-based reasoning questions from feed data."""
    items: list[dict] = []

    for s in summaries:
        provider = s.get("provider", "")
        routes = s.get("route_summary", {}).get("routes", [])
        cal = s.get("calendar_summary", {})

        if not routes or not provider:
            continue

        # Pick a route with valid schedule data
        sched_routes = [
            r for r in routes
            if r.get("first_departure") and r.get("last_departure")
            and r.get("route_short_name")
        ]
        if not sched_routes:
            continue

        route = random.choice(sched_routes[:10])
        name = route["route_short_name"]
        first = route["first_departure"]
        last = route["last_departure"]
        trips = route.get("trip_count", 0)

        # Q: Service hours
        items.append({
            "question": f"What are the operating hours for route {name} by {provider}?",
            "expected_answer": f"Route {name} by {provider} starts service at {_format_time(first)} and ends at {_format_time(last)}.",
            "scoring_criteria": f"Must mention first departure ~{first} and last departure ~{last}",
            "difficulty": "easy",
            "category": "schedule_reasoning",
        })

        # Q: Average frequency estimation
        if trips > 0 and first and last:
            try:
                fh, fm = int(first.split(":")[0]), int(first.split(":")[1])
                lh, lm = int(last.split(":")[0]), int(last.split(":")[1])
                span_minutes = (lh * 60 + lm) - (fh * 60 + fm)
                if span_minutes > 0 and trips > 1:
                    avg_headway = span_minutes / trips
                    items.append({
                        "question": f"Route {name} by {provider} runs {trips:,} trips over approximately {span_minutes // 60} hours. Estimate the average frequency.",
                        "expected_answer": f"With {trips:,} trips over ~{span_minutes // 60} hours ({span_minutes} minutes), the average headway is approximately {avg_headway:.1f} minutes between trips.",
                        "scoring_criteria": f"Must calculate approximately {avg_headway:.0f} minutes between trips",
                        "difficulty": "medium",
                        "category": "schedule_reasoning",
                    })
            except (ValueError, IndexError):
                pass

        # Q: Calendar / service days
        if cal:
            weekday = cal.get("weekday_services", 0)
            weekend = cal.get("weekend_services", 0)
            date_range = cal.get("date_range", [])
            if weekday and date_range:
                items.append({
                    "question": f"How many service patterns does {provider} define for weekdays vs weekends?",
                    "expected_answer": f"{provider} defines {weekday} weekday service patterns and {weekend} weekend service patterns. The schedule covers the date range {date_range[0]} to {date_range[1]}.",
                    "scoring_criteria": f"Must mention {weekday} weekday and {weekend} weekend patterns",
                    "difficulty": "medium",
                    "category": "schedule_reasoning",
                })

    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Category 6: Transit Operations (general knowledge)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_transit_operations(summaries: list[dict]) -> list[dict]:
    """Questions about real-world transit operations."""
    items = [
        {
            "question": "What is headway in public transit?",
            "expected_answer": "Headway is the time interval between consecutive vehicles on the same route passing the same point. For example, a 10-minute headway means a bus comes every 10 minutes. Shorter headways mean more frequent service. Headway is the inverse of frequency.",
            "scoring_criteria": "Must define as time between vehicles on same route",
            "difficulty": "easy",
        },
        {
            "question": "What is deadheading in transit operations?",
            "expected_answer": "Deadheading is when a transit vehicle operates without carrying passengers, typically traveling between the depot and the start of a route, or repositioning between routes. It represents non-revenue service time and distance that operators try to minimize.",
            "scoring_criteria": "Must mention: vehicle moving without passengers, non-revenue service",
            "difficulty": "medium",
        },
        {
            "question": "What is a transit hub and why is it important?",
            "expected_answer": "A transit hub is a major station or stop where multiple transit routes converge, enabling passengers to transfer between services. Hubs are important because they increase network connectivity, reduce the need for direct routes between all points, and allow hub-and-spoke network designs that serve more destinations efficiently.",
            "scoring_criteria": "Must mention multiple routes converging and transfer connectivity",
            "difficulty": "easy",
        },
        {
            "question": "What is the difference between local and express bus service?",
            "expected_answer": "Local service stops at every stop along the route, providing maximum coverage but slower travel. Express service skips intermediate stops, making fewer stops for faster end-to-end travel. Express routes often run on highways or major corridors during peak hours.",
            "scoring_criteria": "Must contrast: local stops at every stop, express skips stops for speed",
            "difficulty": "easy",
        },
        {
            "question": "What is intermodal transit and give an example?",
            "expected_answer": "Intermodal transit involves using multiple modes of transportation in a single journey. For example, a commuter might take a bus to a train station, ride the train downtown, then walk to their destination. GTFS supports this by including multiple route_types and transfer information in a single feed.",
            "scoring_criteria": "Must define multiple modes in one journey and give an example",
            "difficulty": "easy",
        },
        {
            "question": "What is a layover in transit operations?",
            "expected_answer": "A layover is scheduled time at the end of a route where a vehicle waits before starting the return trip. It serves multiple purposes: allows the driver to rest, provides schedule recovery time if the previous trip ran late, and ensures the vehicle departs on time for the next trip.",
            "scoring_criteria": "Must mention scheduled wait time at route end, schedule recovery",
            "difficulty": "medium",
        },
        {
            "question": "What is demand-responsive transit (DRT)?",
            "expected_answer": "Demand-responsive transit is a flexible service where routes and schedules are adjusted based on passenger requests rather than following fixed routes. Examples include dial-a-ride, paratransit, and microtransit. In GTFS, this can be partially represented using continuous_pickup/drop_off or through GTFS-Flex extensions.",
            "scoring_criteria": "Must explain flexible routing based on demand, mention examples",
            "difficulty": "medium",
        },
        {
            "question": "What is the purpose of a transit signal priority (TSP) system?",
            "expected_answer": "Transit signal priority gives buses or trams preferential treatment at traffic signals — extending green lights or shortening red lights to reduce delays. TSP improves schedule adherence, reduces travel time, and makes transit more reliable and attractive to riders.",
            "scoring_criteria": "Must explain preferential signal treatment for transit vehicles",
            "difficulty": "medium",
        },
        {
            "question": "What is a short turn in transit operations?",
            "expected_answer": "A short turn is when a transit vehicle reverses direction before completing its full route, serving only part of the line. It is used to increase frequency on the busiest segment of a route or to recover from delays by reducing the round-trip time.",
            "scoring_criteria": "Must explain turning back before full route, increased frequency on busy segments",
            "difficulty": "hard",
        },
        {
            "question": "What is fare capping and how does it benefit riders?",
            "expected_answer": "Fare capping limits the total amount a rider pays over a period (daily, weekly, monthly). Once the cap is reached, additional trips are free. It benefits riders by providing the equivalent of a pass without requiring an upfront purchase, making transit more equitable for low-income riders who can't afford monthly passes.",
            "scoring_criteria": "Must explain spending limit concept and equity benefit",
            "difficulty": "medium",
        },
        {
            "question": "What is a transit network's coverage vs frequency tradeoff?",
            "expected_answer": "With limited resources, transit agencies must choose between coverage (serving more areas with less frequent service) and frequency (serving fewer routes but with shorter headways). High-frequency networks attract more riders per route but leave some areas unserved. Coverage-oriented networks reach more places but with longer waits.",
            "scoring_criteria": "Must explain the resource tradeoff between area coverage and service frequency",
            "difficulty": "hard",
        },
        {
            "question": "What is a pulse schedule in transit?",
            "expected_answer": "A pulse schedule (or timed-transfer network) is where multiple routes are scheduled to arrive at a central hub simultaneously, allow passenger transfers, then depart together. This creates a 'pulse' of activity at regular intervals and enables reliable connections even with low-frequency routes.",
            "scoring_criteria": "Must explain simultaneous arrival at hub for transfers",
            "difficulty": "hard",
        },
    ]

    # Add data-driven questions about network size
    for s in summaries:
        provider = s.get("provider", "")
        stats = s.get("network_stats", {})
        total_stops = s.get("stop_summary", {}).get("total_stops", 0)
        total_routes = stats.get("total_routes", 0)

        if not provider or not total_stops:
            continue

        items.append({
            "question": f"How large is the {provider} transit network in terms of stops and routes?",
            "expected_answer": f"The {provider} network has {total_stops:,} stops and {total_routes} routes.",
            "scoring_criteria": f"Must state approximately {total_stops:,} stops and {total_routes} routes",
            "difficulty": "easy",
            "category": "transit_operations",
        })

    for item in items:
        item.setdefault("category", "transit_operations")
    return items


# ═══════════════════════════════════════════════════════════════════════════════
# Main: Generate benchmark
# ═══════════════════════════════════════════════════════════════════════════════

def generate_benchmark() -> dict:
    """Generate the complete benchmark dataset."""
    summaries = load_feed_summaries()
    print(f"Loaded {len(summaries)} feed summaries")

    # Generate all categories
    all_items: list[dict] = []

    gtfs_term = generate_gtfs_terminology()
    all_items.extend(gtfs_term)
    print(f"  GTFS Terminology:    {len(gtfs_term)} questions")

    gtfs_val = generate_gtfs_validation()
    all_items.extend(gtfs_val)
    print(f"  GTFS Validation:     {len(gtfs_val)} questions")

    route_q = generate_route_analysis(summaries)
    all_items.extend(route_q)
    print(f"  Route Analysis:      {len(route_q)} questions")

    journey_q = generate_journey_planning()
    all_items.extend(journey_q)
    print(f"  Journey Planning:    {len(journey_q)} questions")

    sched_q = generate_schedule_reasoning(summaries)
    all_items.extend(sched_q)
    print(f"  Schedule Reasoning:  {len(sched_q)} questions")

    ops_q = generate_transit_operations(summaries)
    all_items.extend(ops_q)
    print(f"  Transit Operations:  {len(ops_q)} questions")

    # Add IDs
    for i, item in enumerate(all_items, 1):
        item["id"] = f"BM-{i:04d}"

    # Build benchmark document
    from collections import Counter
    cat_counts = Counter(item["category"] for item in all_items)
    diff_counts = Counter(item["difficulty"] for item in all_items)

    benchmark = {
        "metadata": {
            "name": "UmarTransit Evaluation Benchmark",
            "version": "1.0",
            "description": "Structured evaluation benchmark for transit AI models covering GTFS knowledge, validation, route analysis, journey planning, schedule reasoning, and transit operations.",
            "total_questions": len(all_items),
            "categories": dict(sorted(cat_counts.items())),
            "difficulty_distribution": dict(sorted(diff_counts.items())),
        },
        "questions": all_items,
    }

    print(f"\nTotal benchmark questions: {len(all_items)}")
    print(f"Categories: {dict(sorted(cat_counts.items()))}")
    print(f"Difficulty: {dict(sorted(diff_counts.items()))}")

    return benchmark


def main() -> None:
    benchmark = generate_benchmark()

    with open(BENCHMARK_PATH, "w") as f:
        json.dump(benchmark, f, indent=2, ensure_ascii=False)

    print(f"\nBenchmark saved to: {BENCHMARK_PATH}")


if __name__ == "__main__":
    main()
