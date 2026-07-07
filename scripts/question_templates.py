"""Question/response templates for synthetic dataset generation.

Defines templates across 8 task categories that transform feed statistics
into instruction/response pairs for model training.
"""

from dataclasses import dataclass
from typing import Callable

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


def _route_type_name(rt: int) -> str:
    return ROUTE_TYPE_NAMES.get(rt, f"Unknown (type {rt})")


def _format_time(t: str | None) -> str:
    """Format GTFS time for human-readable output."""
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


def _modes_text(by_type: dict) -> str:
    """Format route type counts into natural text."""
    parts = []
    for rt, count in sorted(by_type.items()):
        name = _route_type_name(int(rt))
        parts.append(f"{count} {name} route{'s' if count != 1 else ''}")
    return ", ".join(parts) if parts else "no routes"


@dataclass
class QuestionTemplate:
    """A template that generates an instruction/response pair from facts."""

    category: str
    template_id: str
    generate: Callable[[dict], dict | None]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 1: Agency Overview
# ═══════════════════════════════════════════════════════════════════════════════

def _agency_modes(facts: dict) -> dict | None:
    name = facts.get("agency_name", "")
    by_type = facts.get("by_type", {})
    if not name or not by_type:
        return None
    modes = _modes_text(by_type)
    total = facts.get("total_routes", 0)
    return {
        "instruction": f"What transit modes does {name} operate?",
        "response": f"{name} operates the following transit services: {modes}. In total, the agency has {total} routes.",
    }


def _agency_modes_v2(facts: dict) -> dict | None:
    name = facts.get("agency_name", "")
    by_type = facts.get("by_type", {})
    if not name or not by_type:
        return None
    modes = _modes_text(by_type)
    return {
        "instruction": f"Describe the types of transit services provided by {name}.",
        "response": f"{name} provides the following transit services: {modes}.",
    }


def _agency_route_count(facts: dict) -> dict | None:
    name = facts.get("agency_name", "")
    total = facts.get("total_routes", 0)
    by_type = facts.get("by_type", {})
    if not name or total == 0:
        return None
    breakdown = ". ".join(
        f"{count} are {_route_type_name(int(rt))} routes"
        for rt, count in sorted(by_type.items())
    )
    return {
        "instruction": f"How many routes does {name} have?",
        "response": f"{name} operates {total} routes. {breakdown}.",
    }


def _agency_route_count_v2(facts: dict) -> dict | None:
    name = facts.get("agency_name", "")
    total = facts.get("total_routes", 0)
    if not name or total == 0:
        return None
    return {
        "instruction": f"Tell me about the size of {name}'s transit network.",
        "response": f"{name} operates a transit network with {total} routes, {facts.get('total_stops', 0)} stops, and approximately {facts.get('total_trips', 0):,} scheduled trips.",
    }


def _agency_timezone(facts: dict) -> dict | None:
    name = facts.get("agency_name", "")
    tz = facts.get("agency_timezone", "")
    if not name or not tz:
        return None
    return {
        "instruction": f"What timezone does {name} operate in?",
        "response": f"{name} operates in the {tz} timezone.",
    }


AGENCY_OVERVIEW_TEMPLATES = [
    QuestionTemplate("agency_overview", "agency_modes_v1", _agency_modes),
    QuestionTemplate("agency_overview", "agency_modes_v2", _agency_modes_v2),
    QuestionTemplate("agency_overview", "agency_route_count_v1", _agency_route_count),
    QuestionTemplate("agency_overview", "agency_route_count_v2", _agency_route_count_v2),
    QuestionTemplate("agency_overview", "agency_timezone", _agency_timezone),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 2: Route Information
# ═══════════════════════════════════════════════════════════════════════════════

def _route_describe(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    short = facts.get("route_short_name", "")
    long_name = facts.get("route_long_name", "")
    rt = facts.get("route_type")
    if not (short or long_name):
        return None
    name = f"{short} ({long_name})" if short and long_name else (short or long_name)
    rt_name = _route_type_name(int(rt)) if rt is not None and rt != "" else "transit"
    trips = facts.get("trip_count", 0)
    stops = facts.get("stop_count", 0)
    resp = f"Route {name} is a {rt_name} service operated by {provider}."
    if trips:
        resp += f" It runs approximately {trips:,} trips."
    if stops:
        resp += f" The route serves {stops} stops."
    headsigns = facts.get("headsigns", [])
    if headsigns:
        resp += f" Destinations include: {', '.join(headsigns[:3])}."
    return {"instruction": f"Describe route {short or long_name} operated by {provider}.", "response": resp}


def _route_describe_v2(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    short = facts.get("route_short_name", "")
    long_name = facts.get("route_long_name", "")
    rt = facts.get("route_type")
    if not (short or long_name):
        return None
    name = short or long_name
    rt_name = _route_type_name(int(rt)) if rt is not None and rt != "" else "transit"
    return {
        "instruction": f"What type of service is route {name} by {provider}?",
        "response": f"Route {name} by {provider} is a {rt_name} service. Its full name is '{long_name}'." if long_name else f"Route {name} by {provider} is a {rt_name} service.",
    }


def _route_list_by_type(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    rt = facts.get("route_type_filter")
    routes = facts.get("routes_of_type", [])
    if not routes or rt is None:
        return None
    rt_name = _route_type_name(int(rt))
    route_names = [r.get("route_short_name") or r.get("route_long_name", "") for r in routes[:15]]
    route_list = ", ".join(n for n in route_names if n)
    return {
        "instruction": f"List all {rt_name.lower()} routes operated by {provider}.",
        "response": f"{provider} operates {len(routes)} {rt_name.lower()} routes: {route_list}{'.' if len(routes) <= 15 else f', and {len(routes) - 15} more.'}",
    }


ROUTE_INFO_TEMPLATES = [
    QuestionTemplate("route_info", "route_describe_v1", _route_describe),
    QuestionTemplate("route_info", "route_describe_v2", _route_describe_v2),
    QuestionTemplate("route_info", "route_list_by_type", _route_list_by_type),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 3: Stop/Station Information
# ═══════════════════════════════════════════════════════════════════════════════

def _stop_location(facts: dict) -> dict | None:
    name = facts.get("stop_name", "")
    lat = facts.get("stop_lat")
    lon = facts.get("stop_lon")
    provider = facts.get("provider", "")
    if not name or not lat or not lon:
        return None
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (ValueError, TypeError):
        return None
    return {
        "instruction": f"Where is the {name} stop located in the {provider} network?",
        "response": f"The {name} stop is located at latitude {lat_f:.4f}, longitude {lon_f:.4f} in the {provider} transit network.",
    }


def _stop_location_v2(facts: dict) -> dict | None:
    name = facts.get("stop_name", "")
    lat = facts.get("stop_lat")
    lon = facts.get("stop_lon")
    if not name or not lat or not lon:
        return None
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (ValueError, TypeError):
        return None
    return {
        "instruction": f"What are the coordinates of {name}?",
        "response": f"{name} is located at coordinates ({lat_f:.4f}, {lon_f:.4f}).",
    }


def _stop_count(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    total = facts.get("total_stops", 0)
    stations = facts.get("station_count", 0)
    if not provider or total == 0:
        return None
    resp = f"The {provider} network has {total:,} stops."
    if stations > 0:
        resp += f" Of these, {stations} are classified as stations (parent stops)."
    return {
        "instruction": f"How many stops are in the {provider} network?",
        "response": resp,
    }


STOP_TEMPLATES = [
    QuestionTemplate("stop_info", "stop_location_v1", _stop_location),
    QuestionTemplate("stop_info", "stop_location_v2", _stop_location_v2),
    QuestionTemplate("stop_info", "stop_count", _stop_count),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 4: Trip & Schedule Analysis
# ═══════════════════════════════════════════════════════════════════════════════

def _route_trip_count(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    name = facts.get("route_short_name") or facts.get("route_long_name", "")
    trips = facts.get("trip_count", 0)
    if not name or not trips:
        return None
    return {
        "instruction": f"How many trips run on route {name} by {provider}?",
        "response": f"Route {name} operated by {provider} has approximately {trips:,} scheduled trips.",
    }


def _route_schedule(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    name = facts.get("route_short_name") or facts.get("route_long_name", "")
    first = facts.get("first_departure")
    last = facts.get("last_departure")
    if not name or not first or not last:
        return None
    return {
        "instruction": f"What are the first and last departure times for route {name} by {provider}?",
        "response": f"Route {name} by {provider} has its first departure at {_format_time(first)} and its last departure at {_format_time(last)}.",
    }


def _route_schedule_v2(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    name = facts.get("route_short_name") or facts.get("route_long_name", "")
    first = facts.get("first_departure")
    last = facts.get("last_departure")
    trips = facts.get("trip_count", 0)
    stops = facts.get("stop_count", 0)
    if not name or not trips:
        return None
    resp = f"Route {name} by {provider} runs {trips:,} trips serving {stops} stops."
    if first and last:
        resp += f" Service starts at {_format_time(first)} and ends at {_format_time(last)}."
    return {
        "instruction": f"Give me a schedule overview of route {name} by {provider}.",
        "response": resp,
    }


SCHEDULE_TEMPLATES = [
    QuestionTemplate("schedule", "route_trip_count", _route_trip_count),
    QuestionTemplate("schedule", "route_schedule_v1", _route_schedule),
    QuestionTemplate("schedule", "route_schedule_v2", _route_schedule_v2),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 5: Transfer Analysis
# ═══════════════════════════════════════════════════════════════════════════════

TRANSFER_TYPE_NAMES = {
    0: "Recommended transfer point",
    1: "Timed transfer (vehicle waits)",
    2: "Minimum time required",
    3: "No transfer possible",
}


def _transfer_info(facts: dict) -> dict | None:
    from_name = facts.get("from_stop_name", "")
    to_name = facts.get("to_stop_name", "")
    tt = facts.get("transfer_type")
    min_time = facts.get("min_transfer_time")
    provider = facts.get("provider", "")
    if not from_name or not to_name:
        return None
    tt_desc = TRANSFER_TYPE_NAMES.get(tt, "a standard transfer") if tt is not None else "a transfer"
    resp = f"There is {tt_desc} between {from_name} and {to_name} in the {provider} network."
    if min_time and min_time > 0:
        resp += f" The minimum transfer time is {min_time} seconds ({min_time // 60} minutes)."
    return {
        "instruction": f"What is the transfer between {from_name} and {to_name} in the {provider} system?",
        "response": resp,
    }


def _transfer_count(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    total = facts.get("total_transfers", 0)
    if not provider or total == 0:
        return None
    return {
        "instruction": f"How many transfer points does {provider} have?",
        "response": f"{provider} has {total:,} defined transfer connections in its network.",
    }


TRANSFER_TEMPLATES = [
    QuestionTemplate("transfer", "transfer_info", _transfer_info),
    QuestionTemplate("transfer", "transfer_count", _transfer_count),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 6: Network Statistics
# ═══════════════════════════════════════════════════════════════════════════════

def _network_overview(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    stats = facts.get("network_stats", {})
    if not provider or not stats:
        return None
    return {
        "instruction": f"Give me an overview of the {provider} transit network.",
        "response": (
            f"The {provider} transit network consists of {stats.get('total_routes', 0)} routes "
            f"serving {stats.get('total_stops', 0):,} stops. "
            f"There are approximately {stats.get('total_trips', 0):,} scheduled trips. "
            f"On average, each route serves about {stats.get('avg_stops_per_route', 0)} stops "
            f"and runs {stats.get('avg_trips_per_route', 0):.0f} trips."
        ),
    }


def _network_overview_v2(facts: dict) -> dict | None:
    provider = facts.get("provider", "")
    stats = facts.get("network_stats", {})
    country = facts.get("country_code", "")
    if not provider or not stats:
        return None
    return {
        "instruction": f"How large is the {provider} transit system?",
        "response": (
            f"{provider} ({country}) operates {stats.get('total_routes', 0)} routes "
            f"with {stats.get('total_stops', 0):,} stops across its network."
        ),
    }


NETWORK_STATS_TEMPLATES = [
    QuestionTemplate("network_stats", "network_overview_v1", _network_overview),
    QuestionTemplate("network_stats", "network_overview_v2", _network_overview_v2),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 7: GTFS Knowledge (static, no Parquet data needed)
# ═══════════════════════════════════════════════════════════════════════════════

GTFS_KNOWLEDGE_PAIRS: list[dict] = [
    # Route types
    {"instruction": "What does route_type 0 mean in GTFS?", "response": "In the GTFS specification, route_type 0 indicates Tram, Streetcar, or Light rail service. This includes any light rail or street level transit system within a metropolitan area.", "category": "gtfs_knowledge", "template_id": "route_type_0"},
    {"instruction": "What does route_type 1 mean in GTFS?", "response": "In the GTFS specification, route_type 1 indicates Subway or Metro service. This refers to any underground rail system within a metropolitan area.", "category": "gtfs_knowledge", "template_id": "route_type_1"},
    {"instruction": "What does route_type 2 mean in GTFS?", "response": "In the GTFS specification, route_type 2 indicates Rail service. This is used for intercity or long-distance rail travel, including commuter rail.", "category": "gtfs_knowledge", "template_id": "route_type_2"},
    {"instruction": "What does route_type 3 mean in GTFS?", "response": "In the GTFS specification, route_type 3 indicates Bus service. This is the most common route type and covers short- and long-distance bus routes.", "category": "gtfs_knowledge", "template_id": "route_type_3"},
    {"instruction": "What does route_type 4 mean in GTFS?", "response": "In the GTFS specification, route_type 4 indicates Ferry service. This is used for short- and long-distance boat routes.", "category": "gtfs_knowledge", "template_id": "route_type_4"},
    # Required files
    {"instruction": "What are the required files in a GTFS feed?", "response": "A valid GTFS feed must include the following required files: agency.txt (transit agency information), routes.txt (transit routes), trips.txt (trips for each route), stops.txt (individual stop locations), stop_times.txt (times a vehicle arrives at and departs from stops), and either calendar.txt or calendar_dates.txt (service dates). Optional files include shapes.txt, transfers.txt, frequencies.txt, fare_attributes.txt, and feed_info.txt.", "category": "gtfs_knowledge", "template_id": "required_files"},
    {"instruction": "What files must a GTFS dataset contain?", "response": "A GTFS dataset must contain these core files: agency.txt, routes.txt, trips.txt, stops.txt, and stop_times.txt. Additionally, at least one of calendar.txt or calendar_dates.txt must be present to define when service operates. All other files such as shapes.txt, transfers.txt, and feed_info.txt are optional.", "category": "gtfs_knowledge", "template_id": "required_files_v2"},
    # File relationships
    {"instruction": "Explain the relationship between trips.txt and stop_times.txt in GTFS.", "response": "In GTFS, trips.txt defines individual trips (journeys) along a route, while stop_times.txt specifies the exact arrival and departure times at each stop for each trip. They are linked by the trip_id field. Each trip in trips.txt can have many entries in stop_times.txt — one for each stop the vehicle visits, ordered by stop_sequence. A trip also references a route_id (from routes.txt) and a service_id (from calendar.txt or calendar_dates.txt).", "category": "gtfs_knowledge", "template_id": "trips_stop_times_rel"},
    {"instruction": "How are routes, trips, and stop_times related in GTFS?", "response": "In GTFS, the hierarchy is: routes → trips → stop_times. A route (routes.txt) represents a group of trips shown to riders as a single service (e.g., 'Red Line'). Each route has many trips (trips.txt), representing individual journeys at specific times. Each trip has many stop_times (stop_times.txt), listing the exact arrival/departure time at each stop along the journey. They are linked by route_id (routes→trips) and trip_id (trips→stop_times).", "category": "gtfs_knowledge", "template_id": "route_trip_st_hierarchy"},
    # Calendar
    {"instruction": "What is the difference between calendar.txt and calendar_dates.txt in GTFS?", "response": "calendar.txt defines regular weekly service patterns using day-of-week flags (monday through sunday) with a start and end date range. calendar_dates.txt defines exceptions to the regular schedule — adding service on specific dates (exception_type=1) or removing service (exception_type=2). A feed can use calendar.txt alone, calendar_dates.txt alone, or both together. When both are present, calendar_dates.txt overrides calendar.txt for the specific dates listed.", "category": "gtfs_knowledge", "template_id": "calendar_vs_dates"},
    # Stops
    {"instruction": "What is the location_type field in GTFS stops.txt?", "response": "The location_type field in stops.txt indicates whether a record represents a stop/platform (0 or blank), a station (1), an entrance/exit (2), a generic node (3), or a boarding area (4). Stations (type 1) serve as parent stops that group related platforms and entrances using the parent_station field. Most individual boarding locations have location_type 0.", "category": "gtfs_knowledge", "template_id": "location_type"},
    # Times
    {"instruction": "Can GTFS times exceed 24:00:00?", "response": "Yes, GTFS allows times greater than 24:00:00 in stop_times.txt. This is used for trips that extend past midnight relative to the service day. For example, a departure time of 25:30:00 means 1:30 AM the day after the service day starts. This convention avoids ambiguity about which calendar day a late-night trip belongs to.", "category": "gtfs_knowledge", "template_id": "time_past_midnight"},
    # What is GTFS
    {"instruction": "What is GTFS?", "response": "GTFS (General Transit Feed Specification) is an open standard for sharing public transit schedule, route, and stop information. Originally developed by Google and TriMet (Portland, OR) in 2005, it defines a common format using CSV files packaged in a ZIP archive. GTFS enables transit agencies to publish their data and allows developers to build applications like trip planners. There are two variants: GTFS Static (scheduled service) and GTFS Realtime (live vehicle positions and predictions).", "category": "gtfs_knowledge", "template_id": "what_is_gtfs"},
    {"instruction": "What does GTFS stand for?", "response": "GTFS stands for General Transit Feed Specification. It is an open data standard that defines a common format for public transportation schedules and associated geographic information. GTFS data is published by transit agencies worldwide and used by applications like Google Maps, Apple Maps, and many transit apps for trip planning.", "category": "gtfs_knowledge", "template_id": "gtfs_acronym"},
    # Shapes
    {"instruction": "What is shapes.txt in GTFS?", "response": "shapes.txt is an optional GTFS file that defines the physical path a vehicle takes along a route. Each shape is a sequence of latitude/longitude points (shape_pt_lat, shape_pt_lon) ordered by shape_pt_sequence. Trips reference shapes via shape_id. Shapes are used to draw route lines on maps and can include shape_dist_traveled for distance calculations.", "category": "gtfs_knowledge", "template_id": "shapes_file"},
    # Transfers
    {"instruction": "What transfer types are defined in GTFS?", "response": "GTFS defines four transfer types in transfers.txt: Type 0 is a recommended transfer point between routes. Type 1 is a timed transfer where the departing vehicle waits for the arriving vehicle. Type 2 requires a minimum transfer time (specified in min_transfer_time). Type 3 means transfers are not possible between the stops.", "category": "gtfs_knowledge", "template_id": "transfer_types"},
    # Frequencies
    {"instruction": "What is frequencies.txt in GTFS?", "response": "frequencies.txt is an optional GTFS file used for routes that operate on regular headways (intervals) rather than fixed schedules. Instead of listing every individual trip time, it specifies a trip pattern with start_time, end_time, and headway_secs (interval in seconds). The exact_times field indicates whether times are exact (1) or approximate (0). This is common for high-frequency metro and bus services.", "category": "gtfs_knowledge", "template_id": "frequencies_file"},
    # Direction
    {"instruction": "What does direction_id mean in GTFS trips.txt?", "response": "The direction_id field in trips.txt indicates the direction of travel for a trip. It uses values 0 and 1 to distinguish between two directions on a route (e.g., outbound vs. inbound, or northbound vs. southbound). The field is optional and the specific meaning of 0 vs 1 depends on the transit agency.", "category": "gtfs_knowledge", "template_id": "direction_id"},
    # Wheelchair
    {"instruction": "How is wheelchair accessibility represented in GTFS?", "response": "GTFS represents wheelchair accessibility in two places. In trips.txt, the wheelchair_accessible field indicates if a vehicle used for the trip can accommodate wheelchairs (0=no info, 1=yes, 2=no). In stops.txt, the wheelchair_boarding field indicates if boarding is possible from the stop (0=no info, 1=some accessible, 2=not possible). These help trip planners filter accessible routes.", "category": "gtfs_knowledge", "template_id": "wheelchair"},
    # Bike
    {"instruction": "How does GTFS handle bicycle information?", "response": "GTFS includes a bikes_allowed field in trips.txt to indicate whether bicycles are permitted on a trip. The values are: 0 or empty means no information, 1 means at least one bicycle can be accommodated, and 2 means no bicycles are allowed. This helps cyclists plan multi-modal trips combining cycling with transit.", "category": "gtfs_knowledge", "template_id": "bikes_allowed"},
    # Feed info
    {"instruction": "What information does feed_info.txt contain in GTFS?", "response": "feed_info.txt is an optional GTFS file that provides metadata about the feed itself, including: feed_publisher_name (organization that publishes the feed), feed_publisher_url (URL of the publisher), feed_lang (default language), feed_start_date and feed_end_date (validity period), and feed_version (version identifier). It helps consumers understand the provenance and currency of the data.", "category": "gtfs_knowledge", "template_id": "feed_info"},
    # Zone
    {"instruction": "What is zone_id in GTFS stops.txt?", "response": "The zone_id field in stops.txt defines the fare zone for a stop. It is used in conjunction with fare_rules.txt to determine the fare for a trip based on the origin and destination zones. Many transit systems use zone-based pricing where fares increase when crossing zone boundaries.", "category": "gtfs_knowledge", "template_id": "zone_id"},
]


# ═══════════════════════════════════════════════════════════════════════════════
# Category 8: Comparative Analysis (generated from cross-feed data)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_comparative_pairs(summaries: list[dict]) -> list[dict]:
    """Generate cross-feed comparison instruction/response pairs."""
    pairs: list[dict] = []

    if not summaries:
        return pairs

    # Sort by various metrics for comparisons
    by_routes = sorted(summaries, key=lambda s: s.get("route_summary", {}).get("total_routes", 0), reverse=True)
    by_stops = sorted(summaries, key=lambda s: s.get("stop_summary", {}).get("total_stops", 0), reverse=True)

    # Most routes
    top = by_routes[0]
    pairs.append({
        "instruction": "Which transit agency in the dataset has the most routes?",
        "response": f"{top['provider']} ({top['country_code']}) has the most routes with {top['route_summary']['total_routes']} routes. "
                     f"The top 5 by route count are: " +
                     ", ".join(f"{s['provider']} ({s['route_summary']['total_routes']})" for s in by_routes[:5]) + ".",
        "category": "comparative",
        "template_id": "most_routes",
        "feed_id": "",
        "provider": "",
    })

    # Most stops
    top = by_stops[0]
    pairs.append({
        "instruction": "Which transit network has the most stops?",
        "response": f"{top['provider']} ({top['country_code']}) has the most stops with {top['stop_summary']['total_stops']:,}. "
                     f"The top 5 by stop count are: " +
                     ", ".join(f"{s['provider']} ({s['stop_summary']['total_stops']:,})" for s in by_stops[:5]) + ".",
        "category": "comparative",
        "template_id": "most_stops",
        "feed_id": "",
        "provider": "",
    })

    # Compare specific pairs
    for i in range(min(len(summaries) - 1, 10)):
        a, b = summaries[i], summaries[i + 1]
        a_routes = a.get("route_summary", {}).get("total_routes", 0)
        b_routes = b.get("route_summary", {}).get("total_routes", 0)
        a_stops = a.get("stop_summary", {}).get("total_stops", 0)
        b_stops = b.get("stop_summary", {}).get("total_stops", 0)

        pairs.append({
            "instruction": f"Compare the transit networks of {a['provider']} and {b['provider']}.",
            "response": (
                f"{a['provider']} ({a['country_code']}) has {a_routes} routes and {a_stops:,} stops. "
                f"{b['provider']} ({b['country_code']}) has {b_routes} routes and {b_stops:,} stops. "
                f"{'The former' if a_routes > b_routes else 'The latter'} has more routes, while "
                f"{'the former' if a_stops > b_stops else 'the latter'} has more stops."
            ),
            "category": "comparative",
            "template_id": "compare_pair",
            "feed_id": "",
            "provider": "",
        })

    # Multi-modal agencies
    multimodal = [
        s for s in summaries
        if len(s.get("route_summary", {}).get("by_type", {})) > 1
    ]
    if multimodal:
        names = [f"{s['provider']} ({len(s['route_summary']['by_type'])} modes)" for s in multimodal[:8]]
        pairs.append({
            "instruction": "Which transit agencies operate multiple transit modes?",
            "response": f"The following agencies operate multiple transit modes: {', '.join(names)}. "
                         f"Multi-modal agencies provide a combination of services such as bus, subway, tram, rail, and ferry.",
            "category": "comparative",
            "template_id": "multimodal_agencies",
            "feed_id": "",
            "provider": "",
        })

    # Countries represented
    countries = {}
    for s in summaries:
        cc = s.get("country_code", "")
        if cc:
            countries.setdefault(cc, []).append(s["provider"])
    if countries:
        country_text = ". ".join(
            f"{cc}: {', '.join(providers)}"
            for cc, providers in sorted(countries.items())
        )
        pairs.append({
            "instruction": "What countries are represented in the transit dataset?",
            "response": f"The dataset covers transit agencies from {len(countries)} countries: {country_text}.",
            "category": "comparative",
            "template_id": "countries",
            "feed_id": "",
            "provider": "",
        })

    return pairs


# ═══════════════════════════════════════════════════════════════════════════════
# All templates combined
# ═══════════════════════════════════════════════════════════════════════════════

ALL_TEMPLATES = (
    AGENCY_OVERVIEW_TEMPLATES
    + ROUTE_INFO_TEMPLATES
    + STOP_TEMPLATES
    + SCHEDULE_TEMPLATES
    + TRANSFER_TEMPLATES
    + NETWORK_STATS_TEMPLATES
)
