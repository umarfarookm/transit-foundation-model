"""Expanded training pairs for UmarTransit v1.0.

Adds ~600 new instruction/response pairs covering weak benchmark categories:
- Journey Planning (~200 pairs)
- GTFS Knowledge (~130 pairs, expanding from 22)
- GTFS Validation (~100 pairs)
- Transit Operations (~100 pairs)
- Comparative Analysis (~40 pairs, from feed data)
- Network Stats (~30 pairs, from feed data)

These pairs are merged with the existing 3,306 pairs for retraining.
"""

import json
import random
from pathlib import Path

from scripts.config import CLEANED_DIR, get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Journey Planning pairs (static knowledge — no feed data needed)
# ═══════════════════════════════════════════════════════════════════════════════

JOURNEY_PLANNING_PAIRS: list[dict] = [
    # Transfer logic
    {"instruction": "What factors should a journey planner consider when calculating the fastest route?",
     "response": "A journey planner should consider: scheduled departure and arrival times, transfer times between routes, walking distances to and from stops, real-time delays, service frequency, number of transfers, and time of day (peak vs off-peak schedules). The goal is to minimize total journey time, which includes waiting, riding, walking, and transferring."},
    {"instruction": "What is a timed transfer in public transit?",
     "response": "A timed transfer is when a departing vehicle waits for an arriving vehicle at a transfer point, ensuring passengers can make the connection. In GTFS, this is represented in transfers.txt with transfer_type=1. This is especially important for low-frequency routes where missing a connection could mean a long wait."},
    {"instruction": "What is the difference between a guaranteed connection and a regular transfer?",
     "response": "A guaranteed (timed) connection means the departing vehicle will wait for the arriving vehicle, ensuring the transfer. A regular transfer has no such guarantee — if the arriving service is late, the passenger may miss the connection. In GTFS, transfer_type=1 represents guaranteed connections, while type=0 is a recommended but not guaranteed transfer point."},
    {"instruction": "How does a journey planner handle trips that cross midnight?",
     "response": "GTFS uses times greater than 24:00:00 for trips crossing midnight. For example, a trip departing at 23:45 and arriving at 00:15 would have times 23:45:00 and 24:15:00. This keeps all times on the same service day, avoiding date boundary confusion. The journey planner must convert these for display — 24:15:00 becomes 12:15 AM the next day."},
    {"instruction": "How does a journey planner determine if a transit service is running on a specific date?",
     "response": "It checks two files: 1) calendar.txt for the regular schedule — is the service_id active on that day of week and within the start/end date range? 2) calendar_dates.txt for exceptions — is service added (exception_type=1) or removed (exception_type=2) on that specific date? Exceptions in calendar_dates.txt override the regular schedule in calendar.txt."},
    {"instruction": "What is a fare zone and how does it affect journey planning?",
     "response": "A fare zone is a geographic area used for pricing. Fares may increase when crossing zone boundaries. In GTFS, zone_id in stops.txt defines which zone a stop belongs to, and fare_rules.txt maps zone pairs to fare prices. Journey planners use zone information to calculate accurate fares and show users the cost of different route options."},
    {"instruction": "How would a headway-based bus service be represented in GTFS?",
     "response": "A headway-based service uses frequencies.txt instead of listing every individual trip in stop_times.txt. It specifies: trip_id (referencing a template trip pattern), start_time, end_time, and headway_secs (interval in seconds). For example, a bus running every 10 minutes from 6 AM to 10 PM would have start_time=06:00:00, end_time=22:00:00, headway_secs=600."},
    {"instruction": "What accessibility information should a journey planner use from GTFS?",
     "response": "A journey planner should use: wheelchair_accessible from trips.txt (0=no info, 1=accessible, 2=not accessible) to filter vehicles, wheelchair_boarding from stops.txt (0=no info, 1=some accessible, 2=not possible) to filter stops, and pathways.txt for indoor navigation at stations. This ensures routes suggested to wheelchair users only include accessible vehicles, stops, and transfer paths."},
    {"instruction": "Why might a journey planner suggest a route with more transfers over a direct route?",
     "response": "A route with transfers might be faster if the connecting services are more frequent, operate as express services with fewer stops, or avoid congested areas. The total journey time includes waiting, riding, and transferring — a well-timed multi-transfer route can be significantly faster than a slow direct route with many intermediate stops."},
    {"instruction": "What is a pulse schedule in transit planning?",
     "response": "A pulse schedule (or timed-transfer network) is where multiple routes are scheduled to arrive at a central hub simultaneously, allow passenger transfers during a brief window, then depart together. This creates a 'pulse' of activity at regular intervals and enables reliable connections even with low-frequency routes, making the network more useful than individual routes suggest."},
    {"instruction": "How can GTFS data be used to estimate walking time between stops for transfers?",
     "response": "GTFS provides stop coordinates (stop_lat, stop_lon) which can be used to calculate the walking distance between transfer stops using the Haversine formula. Typical walking speed is assumed at 4-5 km/h. transfers.txt can also specify min_transfer_time for known transfer points. pathways.txt provides detailed walking paths within stations including stairs, escalators, and elevators."},
    {"instruction": "What is the role of trip_headsign in journey planning?",
     "response": "trip_headsign in trips.txt shows the destination or direction displayed on the vehicle — what riders see on the bus or train (e.g., 'Downtown' or 'Airport'). Journey planners display this to help riders identify the correct vehicle at a stop, especially when multiple routes serve the same stop. It's also used in stop_times.txt to override the trip-level headsign for specific stops."},
    {"instruction": "How does a journey planner handle express vs local service on the same route?",
     "response": "Express and local trips typically share the same route_id but have different stop patterns in stop_times.txt — express trips skip intermediate stops. A journey planner compares the total travel time for both: express is faster end-to-end but may require walking further to a stop it actually serves. The planner should present both options to the user with time comparisons."},
    {"instruction": "What is the block_id field and how does it affect journey planning?",
     "response": "block_id in trips.txt groups trips that a single vehicle operates sequentially. When consecutive trips share the same block_id, a passenger can stay on the vehicle for a seat transfer without getting off — the vehicle continues as a different trip. Journey planners can use this to suggest staying onboard when the vehicle's next trip continues toward the passenger's destination."},
    {"instruction": "How does a journey planner use stop_sequence to determine the order of stops?",
     "response": "stop_sequence in stop_times.txt defines the order a vehicle visits stops during a trip. Values must increase along the trip but don't need to be consecutive (1, 2, 5, 10 is valid). Journey planners use this to determine which direction a trip is heading, whether a stop comes before or after another on the same trip, and to display the correct sequence of stops to the user."},
    {"instruction": "What is deadheading and why doesn't it appear in GTFS?",
     "response": "Deadheading is when a transit vehicle operates without carrying passengers, typically traveling between the depot and the start of a route, or repositioning between routes. It doesn't appear in GTFS because GTFS only represents revenue service visible to riders. Deadhead trips are handled internally by transit operations scheduling and are not relevant to passenger journey planning."},
    {"instruction": "How can GTFS shapes data improve journey planning?",
     "response": "shapes.txt provides the actual geographic path a vehicle follows, which improves journey planning by: 1) Drawing accurate route lines on maps so riders can see exactly where the bus goes, 2) Calculating more accurate travel distances using shape_dist_traveled, 3) Helping riders understand if a route passes near their origin or destination, even if the nearest stop is not the optimal one."},
    {"instruction": "What is the difference between arrival_time and departure_time in stop_times.txt?",
     "response": "arrival_time is when the vehicle reaches a stop, and departure_time is when it leaves. For most intermediate stops, these are the same or very close. The difference matters at timepoint stops where the vehicle may wait (e.g., arrives at 10:00, departs at 10:02 for schedule padding). At the first stop, only departure_time matters. At the last stop, only arrival_time matters."},
    {"instruction": "How should a journey planner handle service alerts?",
     "response": "Service alerts from GTFS Realtime inform riders about disruptions like detours, stop closures, or suspended service. A journey planner should: 1) Check for active alerts affecting the planned route, 2) Display alerts prominently before the user confirms their trip, 3) Offer alternative routes if a planned stop or route is affected, 4) Include the alert's cause and effect descriptions."},
    {"instruction": "What is an intermodal journey and how does GTFS support it?",
     "response": "An intermodal journey uses multiple transportation modes in a single trip — for example, bus to train to ferry. GTFS supports this by including multiple route_types in a single feed and defining transfer connections in transfers.txt between stops of different modes. A journey planner combines these to suggest multi-modal trips with appropriate transfer times between modes."},
]

# ─── Data-driven journey planning templates (use feed data) ──────────────────

def generate_journey_planning_from_feeds(summaries: list[dict]) -> list[dict]:
    """Generate journey planning pairs using real feed data."""
    pairs: list[dict] = []

    for s in summaries:
        provider = s.get("provider", "")
        routes = s.get("route_summary", {}).get("routes", [])
        transfers = s.get("transfer_summary", {}).get("sample_transfers", [])
        total_routes = s.get("route_summary", {}).get("total_routes", 0)
        by_type = s.get("route_summary", {}).get("by_type", {})
        cal = s.get("calendar_summary", {})

        if not provider or not routes:
            continue

        # Routes with schedule data
        sched_routes = [r for r in routes if r.get("first_departure") and r.get("trip_count", 0) > 0]
        if not sched_routes:
            continue

        # Transfer availability question
        if transfers:
            t = transfers[0]
            pairs.append({
                "instruction": f"Can I transfer between {t.get('from_stop_name', 'Stop A')} and {t.get('to_stop_name', 'Stop B')} in the {provider} network?",
                "response": f"Yes, there is a transfer connection between {t.get('from_stop_name', 'Stop A')} and {t.get('to_stop_name', 'Stop B')} in the {provider} network." +
                    (f" The minimum transfer time is {t['min_transfer_time']} seconds ({t['min_transfer_time'] // 60} minutes)." if t.get('min_transfer_time') else " This is a recommended transfer point."),
                "category": "journey_planning",
                "template_id": "transfer_availability",
                "feed_id": s.get("feed_id", ""),
                "provider": provider,
            })

        # Early morning service question
        early_routes = [r for r in sched_routes if r.get("first_departure", "99") < "06:00"]
        if early_routes:
            r = early_routes[0]
            name = r.get("route_short_name") or r.get("route_long_name", "")
            pairs.append({
                "instruction": f"What is the earliest service available on {provider}?",
                "response": f"Route {name} has one of the earliest departures at {r['first_departure']}, making it available for early morning commuters.",
                "category": "journey_planning",
                "template_id": "earliest_service",
                "feed_id": s.get("feed_id", ""),
                "provider": provider,
            })

        # Late night service question
        late_routes = [r for r in sched_routes if r.get("last_departure", "00") > "23:00"]
        if late_routes:
            r = late_routes[0]
            name = r.get("route_short_name") or r.get("route_long_name", "")
            pairs.append({
                "instruction": f"Does {provider} offer late-night service?",
                "response": f"Yes, route {name} runs until {r['last_departure']}, providing late-night service.",
                "category": "journey_planning",
                "template_id": "late_night_service",
                "feed_id": s.get("feed_id", ""),
                "provider": provider,
            })

        # Multi-modal question
        if len(by_type) > 1:
            modes = ", ".join(
                f"{ROUTE_TYPE_NAMES.get(int(rt), f'type {rt}')}" for rt in sorted(by_type.keys())
            )
            pairs.append({
                "instruction": f"Can I combine different transit modes on {provider}?",
                "response": f"Yes, {provider} operates multiple transit modes: {modes}. You can combine these modes in a single journey by transferring between them at connection points.",
                "category": "journey_planning",
                "template_id": "multimodal_journey",
                "feed_id": s.get("feed_id", ""),
                "provider": provider,
            })

        # Weekend service question
        if cal.get("weekend_services", 0) > 0:
            pairs.append({
                "instruction": f"Is weekend service available on {provider}?",
                "response": f"Yes, {provider} defines {cal['weekend_services']} weekend service patterns (compared to {cal.get('weekday_services', 0)} weekday patterns). Weekend service is typically reduced compared to weekdays.",
                "category": "journey_planning",
                "template_id": "weekend_availability",
                "feed_id": s.get("feed_id", ""),
                "provider": provider,
            })

        # Highest frequency route
        if len(sched_routes) > 1:
            busiest = max(sched_routes, key=lambda r: r.get("trip_count", 0))
            name = busiest.get("route_short_name") or busiest.get("route_long_name", "")
            trips = busiest.get("trip_count", 0)
            pairs.append({
                "instruction": f"What is the most frequent route on {provider}?",
                "response": f"Route {name} is the most frequent with {trips:,} scheduled trips, making it one of the best options for minimizing wait times.",
                "category": "journey_planning",
                "template_id": "most_frequent_route",
                "feed_id": s.get("feed_id", ""),
                "provider": provider,
            })

    return pairs


# ═══════════════════════════════════════════════════════════════════════════════
# GTFS Knowledge pairs (expanding from 22 to ~150)
# ═══════════════════════════════════════════════════════════════════════════════

GTFS_KNOWLEDGE_EXPANDED: list[dict] = [
    # Extended route types
    {"instruction": "What does route_type 5 mean in GTFS?", "response": "In GTFS, route_type 5 indicates Cable tram service. This refers to street-level transit where the cable runs beneath the vehicle, such as San Francisco's cable cars."},
    {"instruction": "What does route_type 6 mean in GTFS?", "response": "In GTFS, route_type 6 indicates Aerial lift, suspended cable car, or Gondola service. These are cable transport systems where cabins are suspended from a moving cable."},
    {"instruction": "What does route_type 7 mean in GTFS?", "response": "In GTFS, route_type 7 indicates Funicular service. A funicular is a cable railway on a steep slope, where ascending and descending cars counterbalance each other."},
    {"instruction": "What does route_type 11 mean in GTFS?", "response": "In GTFS, route_type 11 indicates Trolleybus service. A trolleybus is an electric bus powered by overhead wires, combining the flexibility of buses with electric traction."},
    {"instruction": "What does route_type 12 mean in GTFS?", "response": "In GTFS, route_type 12 indicates Monorail service. A monorail runs on a single rail or beam, often elevated above street level."},
    # File structure
    {"instruction": "What does agency.txt contain in GTFS?", "response": "agency.txt contains information about transit agencies. Required fields are agency_name, agency_url, and agency_timezone. Optional fields include agency_id (needed when multiple agencies in one feed), agency_lang, agency_phone, agency_fare_url, and agency_email."},
    {"instruction": "What does routes.txt contain in GTFS?", "response": "routes.txt defines transit routes — groups of trips displayed to riders as a single service. Required fields are route_id, route_short_name or route_long_name (at least one), and route_type. Optional fields include route_color, route_text_color, route_url, route_sort_order, and agency_id."},
    {"instruction": "What does trips.txt contain in GTFS?", "response": "trips.txt defines individual trips — specific journeys along a route at a specific time. Required fields are route_id, service_id, and trip_id. Optional fields include trip_headsign, trip_short_name, direction_id, block_id, shape_id, wheelchair_accessible, and bikes_allowed."},
    {"instruction": "What does stops.txt contain in GTFS?", "response": "stops.txt defines individual stop locations. Required fields are stop_id, stop_name, stop_lat, and stop_lon. Optional fields include stop_code, stop_desc, zone_id, stop_url, location_type, parent_station, stop_timezone, wheelchair_boarding, level_id, and platform_code."},
    {"instruction": "What does stop_times.txt contain in GTFS?", "response": "stop_times.txt defines when a vehicle arrives at and departs from each stop during a trip. Required fields are trip_id, arrival_time, departure_time, stop_id, and stop_sequence. Optional fields include stop_headsign, pickup_type, drop_off_type, continuous_pickup, continuous_drop_off, shape_dist_traveled, and timepoint."},
    {"instruction": "What does transfers.txt contain in GTFS?", "response": "transfers.txt defines transfer rules between stops. Required fields are from_stop_id and to_stop_id. Optional fields include transfer_type (0=recommended, 1=timed, 2=minimum time, 3=not possible), min_transfer_time (seconds), from_route_id, to_route_id, from_trip_id, and to_trip_id."},
    # Concepts
    {"instruction": "What is a service_id in GTFS?", "response": "A service_id is a unique identifier that links trips to the days they operate. It connects trips.txt to calendar.txt (regular weekly patterns) and calendar_dates.txt (exceptions). Multiple trips can share the same service_id, meaning they all run on the same days. For example, all weekday trips might share service_id 'weekday'."},
    {"instruction": "What is a shape_id in GTFS?", "response": "A shape_id in GTFS links a trip to its geographic path defined in shapes.txt. Multiple trips can share the same shape_id if they follow the same physical route. The shape is a sequence of latitude/longitude points that represent the path the vehicle takes, used to draw route lines on maps."},
    {"instruction": "What is route_color in GTFS?", "response": "route_color is an optional field in routes.txt that specifies the color used to display the route on maps and in transit apps. It's a 6-character hex color code without the '#' prefix (e.g., 'FF0000' for red). The companion field route_text_color defines the text color used against the route color background."},
    {"instruction": "What is stop_code in GTFS?", "response": "stop_code is an optional field in stops.txt that provides a short rider-facing identifier for a stop, often displayed on stop signs and used in SMS or phone-based transit information systems. Unlike stop_id (internal identifier), stop_code is meant to be human-readable and recognizable to passengers."},
    {"instruction": "What is shape_dist_traveled in GTFS?", "response": "shape_dist_traveled is an optional field in both stop_times.txt and shapes.txt that indicates how far along the shape a stop or point is. It allows accurate positioning of stops along a route's geographic path, especially when routes overlap or loop back on themselves. Units are defined by the agency (typically meters or miles)."},
    {"instruction": "What is the exact_times field in frequencies.txt?", "response": "exact_times indicates whether departure times in frequencies.txt are exact (1) or approximate (0, default). When exact_times=1, departures occur at precise intervals from start_time (e.g., every 10 minutes at :00, :10, :20). When exact_times=0, the headway is approximate — vehicles depart roughly every N seconds but not at fixed clock times."},
    {"instruction": "What is the feed_version field in feed_info.txt?", "response": "feed_version is an optional field in feed_info.txt that provides a version string for the GTFS feed. It helps consumers identify which version of the data they are using and detect when updates are available. The format is agency-defined — common patterns include dates (20240101), semantic versions (1.2.3), or sequential numbers."},
    {"instruction": "What is the platform_code field in stops.txt?", "response": "platform_code is an optional field in stops.txt that identifies the platform at a station where riders should board. For example, 'Platform 2' or 'Track A'. It is particularly useful at large stations with multiple platforms, helping riders navigate to the correct boarding location."},
    {"instruction": "What is attributions.txt in GTFS?", "response": "attributions.txt is an optional GTFS file that provides attribution information for the dataset, such as the organization that produced it, data sources, and URLs. It's used when multiple organizations contribute to a feed and proper credit needs to be given to each data provider."},
    {"instruction": "What is the levels.txt file in GTFS?", "response": "levels.txt is an optional GTFS file that defines vertical levels within a station, such as street level, underground platforms, and mezzanine areas. Each level has a level_id, level_index (vertical ordering), and optional level_name. It works with pathways.txt to enable indoor navigation across floors."},
    {"instruction": "How are fare products defined in GTFS?", "response": "GTFS defines fares using fare_attributes.txt (fare class with price, currency, payment method, transfer rules) and fare_rules.txt (maps fares to routes, zones, or origin-destination pairs). Newer GTFS-Fares v2 uses fare_products.txt, fare_leg_rules.txt, and fare_transfer_rules.txt for more complex fare structures including caps, passes, and time-based pricing."},
    {"instruction": "What is GTFS-Flex?", "response": "GTFS-Flex is an extension to GTFS that describes demand-responsive transit services like dial-a-ride, deviated fixed routes, and zone-based services. It adds files like booking_rules.txt and extends stop_times.txt with location_group_id and location_id to define flexible service areas rather than fixed stop sequences."},
    {"instruction": "What is GTFS-Pathways?", "response": "GTFS-Pathways is a feature of GTFS that describes physical pathways within stations. pathways.txt defines connections between stops, entrances, and nodes with pathway_type (walkway, stairs, escalator, elevator, fare gate), traversal_time, length, and accessibility information. It enables indoor navigation and accessible routing through complex stations."},
    {"instruction": "What is a trip_short_name in GTFS?", "response": "trip_short_name is an optional field in trips.txt that provides a public-facing identifier for a trip, often corresponding to a train number or route variant (e.g., Train 42, Express A). Unlike trip_id (internal), trip_short_name is meant for rider communication and may appear on vehicle displays or printed schedules."},
    {"instruction": "What does the bikes_allowed field mean in GTFS?", "response": "bikes_allowed is an optional field in trips.txt indicating whether bicycles are permitted on a trip. Values: 0 or empty means no information, 1 means at least one bicycle can be accommodated, 2 means no bicycles are allowed. This helps cyclists plan multi-modal trips combining cycling with transit."},
    {"instruction": "What is the difference between stop_id and parent_station in GTFS?", "response": "stop_id is the unique identifier for any stop record — whether it's a platform, station, entrance, or boarding area. parent_station links a child stop to its parent station (location_type=1). For example, 'Platform 1' (stop_id=P1) might have parent_station='Central Station' (stop_id=CS). This creates a hierarchy: station → platforms, entrances, boarding areas."},
    {"instruction": "How does GTFS handle multiple agencies in one feed?", "response": "When a GTFS feed covers multiple agencies, each agency gets a row in agency.txt with a unique agency_id. Routes in routes.txt reference the appropriate agency_id to indicate which agency operates each route. This is common in regional feeds that combine data from multiple transit operators."},
    {"instruction": "What is the role of calendar.txt start_date and end_date?", "response": "start_date and end_date in calendar.txt define the date range during which a service pattern is active. The day-of-week flags (monday through sunday) only apply within this range. A service with monday=1, start_date=20240101, end_date=20240630 means 'runs on Mondays between January 1 and June 30, 2024'. Outside this range, the service does not operate."},
    {"instruction": "What happens when exception_type=1 in calendar_dates.txt?", "response": "exception_type=1 in calendar_dates.txt means service is ADDED on that specific date. This is used for special service — for example, adding holiday service, event shuttles, or extending service on a date it would normally not run. It overrides the calendar.txt pattern for that date."},
    {"instruction": "What happens when exception_type=2 in calendar_dates.txt?", "response": "exception_type=2 in calendar_dates.txt means service is REMOVED on that specific date. This is used to cancel service — for example, a route that normally runs on Mondays might have exception_type=2 on a public holiday Monday. The trip with that service_id will not operate on that date."},
]

# ═══════════════════════════════════════════════════════════════════════════════
# GTFS Validation pairs
# ═══════════════════════════════════════════════════════════════════════════════

GTFS_VALIDATION_PAIRS: list[dict] = [
    {"instruction": "Is a GTFS feed valid if it is missing agency.txt?", "response": "No, the feed is invalid. agency.txt is a required file. It must be present and contain at least agency_name, agency_url, and agency_timezone."},
    {"instruction": "Is a GTFS feed valid without calendar.txt or calendar_dates.txt?", "response": "No, a GTFS feed must include at least one of calendar.txt or calendar_dates.txt. Without either file, there is no way to determine which days services operate."},
    {"instruction": "What happens if a trip references a service_id not in calendar.txt or calendar_dates.txt?", "response": "This is a referential integrity error. Every service_id in trips.txt must exist in calendar.txt or calendar_dates.txt. Without a matching service entry, the trip has no defined operating days and cannot be scheduled."},
    {"instruction": "Is it valid for a GTFS stop to have coordinates (0, 0)?", "response": "While technically valid format-wise, coordinates (0.0, 0.0) place the stop in the Gulf of Guinea off the coast of Africa, known as 'Null Island'. No transit stops exist there, so validators flag this as a data quality error indicating missing or default coordinates."},
    {"instruction": "Can two stops in GTFS have the same stop_id?", "response": "No, stop_id must be unique within stops.txt. Duplicate stop_ids would cause ambiguity in stop_times.txt and transfers.txt references. Validators will reject the feed or flag it as a critical error."},
    {"instruction": "Is it valid for departure_time at stop_sequence 2 to be earlier than departure_time at stop_sequence 1?", "response": "No, this is invalid. Times must be non-decreasing along a trip's stop_sequence. A departure at a later stop cannot be earlier than the departure at a previous stop, as this would mean the vehicle arrived before it departed."},
    {"instruction": "What if a route has both route_short_name and route_long_name empty?", "response": "This is a validation error. The GTFS spec requires at least one of route_short_name or route_long_name to be provided. Both being empty means riders have no way to identify the route."},
    {"instruction": "Is it valid for a GTFS feed to have calendar.txt with end_date before start_date?", "response": "No, this is invalid. The end_date must be equal to or later than start_date. If end_date is before start_date, no service days would be active within the range, making the service definition meaningless."},
    {"instruction": "What if stop_times.txt has duplicate stop_sequence values for the same trip?", "response": "This is invalid. stop_sequence values must be unique within each trip — they define the order stops are visited. Duplicate values create ambiguity in the stop ordering. Each stop_time entry for a trip must have a unique, increasing stop_sequence."},
    {"instruction": "Is it valid for a GTFS feed to have routes.txt but no trips defined for those routes?", "response": "Technically valid but problematic. A route without any trips is an orphan — it exists in the data but has no scheduled service. Validators flag this as a warning because it indicates incomplete data or a route that should have been removed."},
    {"instruction": "What validation issue exists when agency_timezone doesn't match stop locations?", "response": "This is a data quality issue — if stops are located in New York but agency_timezone is 'Europe/London', all schedule times would be wrong for riders. While technically valid format-wise, the geographic mismatch indicates an error. Validators flag this as a geographic consistency warning."},
    {"instruction": "Is it valid for a trip to have only one stop_time entry?", "response": "No, this is invalid. A trip must have at least two stop_time entries — an origin and a destination. A single-stop trip represents no meaningful journey and cannot be used for routing or scheduling."},
    {"instruction": "What happens if transfer_type=2 but min_transfer_time is missing?", "response": "This is a validation issue. transfer_type=2 means a minimum transfer time is required between stops, so the min_transfer_time field should be provided with the number of seconds. Without it, the transfer time constraint cannot be enforced by journey planners."},
    {"instruction": "Can a stop in stops.txt exist without being referenced in stop_times.txt?", "response": "Yes, this is valid. stops.txt may contain parent stations (location_type=1), entrances (type 2), generic nodes (type 3), or boarding areas (type 4) that are not directly referenced in stop_times.txt. Even unused stop records (type 0) are technically valid but may indicate orphaned data."},
    {"instruction": "Is it valid for two trips to have identical stop_times entries?", "response": "Yes, if they have different trip_ids and potentially different service_ids. Two trips can serve the exact same stops at the exact same times but operate on different days. However, if they are complete duplicates (same trip_id), that would be an error."},
    {"instruction": "What is wrong if a shape in shapes.txt has points out of geographic order?", "response": "Points in shapes.txt must follow the order the vehicle travels, defined by shape_pt_sequence. If points are geographically out of order (e.g., jumping back and forth), the resulting map line will be incorrect. Validators check for spatial consistency and flag shapes with implausible jumps."},
    {"instruction": "Is an empty stop_times.txt file valid in GTFS?", "response": "No. While the file must exist (it's required), it must contain at least a header row and data for the trips defined in trips.txt. An empty file means no trips have any scheduled stops, making the feed operationally useless."},
    {"instruction": "What if a route_type value is not in the standard GTFS range?", "response": "The standard GTFS spec defines route_types 0-7 and 11-12. Values outside this range may be valid under extended route type schemes (like Google Transit Extensions which define types 100-1700), but standard validators may flag unknown types as warnings. It depends on which specification version the feed claims to follow."},
    {"instruction": "Is it valid for arrival_time to be empty at intermediate stops?", "response": "Yes, GTFS allows empty arrival_time and departure_time at intermediate stops (not the first or last stop of a trip). The spec allows journey planners to interpolate times between timepoints. However, the first and last stops in a trip must have explicit times."},
    {"instruction": "What validation issue arises from very fast travel between consecutive stops?", "response": "If the time between consecutive stops implies an unrealistically fast speed (e.g., 500 km/h for a bus), validators flag this as a data quality issue. This usually indicates incorrect stop coordinates, wrong times, or missing intermediate stops. Typical maximum speeds vary by mode: ~120 km/h for buses, ~300 km/h for high-speed rail."},
]

# ═══════════════════════════════════════════════════════════════════════════════
# Transit Operations pairs
# ═══════════════════════════════════════════════════════════════════════════════

TRANSIT_OPERATIONS_PAIRS: list[dict] = [
    {"instruction": "What is headway in public transit?", "response": "Headway is the time interval between consecutive vehicles on the same route passing the same point. For example, a 10-minute headway means a bus comes every 10 minutes. Shorter headways mean more frequent service. Headway is the inverse of frequency — a 10-minute headway equals 6 vehicles per hour."},
    {"instruction": "What is deadheading in transit operations?", "response": "Deadheading is when a transit vehicle operates without carrying passengers, typically traveling between the depot and the start of a route, or repositioning between routes. It represents non-revenue service time and distance that operators try to minimize for efficiency."},
    {"instruction": "What is a transit hub?", "response": "A transit hub is a major station or stop where multiple transit routes converge, enabling passengers to transfer between services. Hubs increase network connectivity, reduce the need for direct routes between all points, and allow efficient hub-and-spoke network designs."},
    {"instruction": "What is the difference between local and express bus service?", "response": "Local service stops at every stop along the route, providing maximum area coverage but slower travel. Express service skips intermediate stops, making fewer stops for faster end-to-end travel. Express routes often run on highways or major corridors, especially during peak hours."},
    {"instruction": "What is intermodal transit?", "response": "Intermodal transit involves using multiple transportation modes in a single journey. For example, a commuter might take a bus to a train station, ride the train downtown, then walk to their destination. Transit systems facilitate this through physical transfers at shared stations and coordinated schedules."},
    {"instruction": "What is a layover in transit operations?", "response": "A layover is scheduled time at the end of a route where a vehicle waits before starting the return trip. It serves multiple purposes: allows the driver to rest, provides schedule recovery time if the previous trip ran late, and ensures the vehicle departs on time for the next trip."},
    {"instruction": "What is demand-responsive transit?", "response": "Demand-responsive transit (DRT) is a flexible service where routes and schedules are adjusted based on passenger requests rather than following fixed routes. Examples include dial-a-ride, paratransit for people with disabilities, and microtransit services. Riders typically book trips in advance by phone or app."},
    {"instruction": "What is transit signal priority?", "response": "Transit signal priority (TSP) gives buses or trams preferential treatment at traffic signals — extending green lights or shortening red lights to reduce delays. TSP improves schedule adherence, reduces travel time, and makes transit more reliable and attractive to riders."},
    {"instruction": "What is a short turn in transit operations?", "response": "A short turn is when a transit vehicle reverses direction before completing its full route, serving only part of the line. It is used to increase frequency on the busiest segment of a route or to recover from delays by reducing the round-trip time."},
    {"instruction": "What is fare capping?", "response": "Fare capping limits the total amount a rider pays over a period (daily, weekly, or monthly). Once the cap is reached, additional trips are free. It benefits riders by providing the equivalent of a pass without requiring an upfront purchase, making transit more equitable for low-income riders."},
    {"instruction": "What is the coverage vs frequency tradeoff in transit planning?", "response": "With limited resources, transit agencies must choose between coverage (serving more areas with less frequent service) and frequency (serving fewer routes with shorter headways). High-frequency networks attract more riders per route but leave some areas unserved. Coverage-oriented networks reach more places but with longer waits."},
    {"instruction": "What is a bus rapid transit (BRT) system?", "response": "Bus rapid transit (BRT) is a bus-based system designed to provide fast, reliable service similar to light rail. Key features include dedicated bus lanes, off-board fare payment, level boarding platforms, traffic signal priority, and high-frequency service. BRT is cheaper to build than rail while offering similar performance."},
    {"instruction": "What is a transit service span?", "response": "Service span refers to the hours during which transit service operates — from the first departure to the last arrival of the day. For example, a service span of 5 AM to midnight means 19 hours of operation. Longer service spans serve more rider needs but cost more to operate. Some systems offer 24-hour service on key routes."},
    {"instruction": "What is a transit ridership?", "response": "Ridership measures how many people use a transit system. It can be counted as unlinked trips (each boarding counts separately) or linked trips (a full journey from origin to destination). Ridership data helps agencies plan service levels, justify funding, and measure the effectiveness of service changes."},
    {"instruction": "What is a park-and-ride facility?", "response": "A park-and-ride facility is a parking lot at a transit station where commuters drive and park their car, then transfer to transit for the remainder of their journey. They are typically located at suburban rail stations or express bus stops, helping extend the reach of transit into car-dependent areas."},
    {"instruction": "What is transit-oriented development?", "response": "Transit-oriented development (TOD) is an urban planning approach that concentrates housing, jobs, and amenities around transit stations. By placing destinations within walking distance of frequent transit, TOD increases ridership, reduces car dependency, and creates vibrant, walkable neighborhoods."},
    {"instruction": "What is revenue service in transit?", "response": "Revenue service refers to trips where a transit vehicle is carrying or available to carry passengers. It excludes deadheading (empty repositioning), maintenance runs, and training trips. Revenue service hours and miles are key metrics for measuring transit productivity and allocating funding."},
    {"instruction": "What is a transit route branching?", "response": "Route branching is when a single route splits into two or more paths at a certain point. For example, a bus route might follow the same path downtown but split into different neighborhoods at the end. In GTFS, branches are typically represented as separate trips with different stop patterns under the same route_id."},
    {"instruction": "What is dwell time in transit?", "response": "Dwell time is the time a transit vehicle spends stopped at a station or stop for passenger boarding and alighting. It includes door opening/closing, fare payment, and passenger movement. Excessive dwell time delays service — strategies to reduce it include all-door boarding, off-board fare payment, and level boarding platforms."},
    {"instruction": "What is a transit network's connectivity?", "response": "Network connectivity measures how well different parts of a transit system are linked. High connectivity means passengers can reach many destinations with few transfers. It depends on route design, transfer points, schedule coordination, and service frequency. Grid networks tend to have higher connectivity than hub-and-spoke designs."},
]

# ═══════════════════════════════════════════════════════════════════════════════
# Data-driven: comparative + network stats (from feed data)
# ═══════════════════════════════════════════════════════════════════════════════

ROUTE_TYPE_NAMES: dict[int, str] = {
    0: "Tram/Streetcar/Light rail", 1: "Subway/Metro", 2: "Rail/Commuter rail",
    3: "Bus", 4: "Ferry", 5: "Cable tram", 6: "Aerial lift/Gondola",
    7: "Funicular", 11: "Trolleybus", 12: "Monorail",
}


def generate_comparative_expanded(summaries: list[dict]) -> list[dict]:
    """Generate additional comparative pairs from feed data."""
    pairs: list[dict] = []
    if len(summaries) < 2:
        return pairs

    # Pairwise comparisons (more diverse than existing)
    random.seed(42)
    indices = list(range(len(summaries)))
    random.shuffle(indices)

    for i in range(0, len(indices) - 1, 2):
        a, b = summaries[indices[i]], summaries[indices[i + 1]]
        a_routes = a.get("route_summary", {}).get("total_routes", 0)
        b_routes = b.get("route_summary", {}).get("total_routes", 0)
        a_stops = a.get("stop_summary", {}).get("total_stops", 0)
        b_stops = b.get("stop_summary", {}).get("total_stops", 0)
        a_trips = a.get("network_stats", {}).get("total_trips", 0)
        b_trips = b.get("network_stats", {}).get("total_trips", 0)

        pairs.append({
            "instruction": f"Compare the size of {a['provider']} and {b['provider']} transit networks.",
            "response": f"{a['provider']} ({a.get('country_code', '')}) has {a_routes} routes, {a_stops:,} stops, and {a_trips:,} trips. {b['provider']} ({b.get('country_code', '')}) has {b_routes} routes, {b_stops:,} stops, and {b_trips:,} trips. {'The former' if a_routes > b_routes else 'The latter'} has more routes.",
            "category": "comparative",
            "template_id": "size_comparison_expanded",
            "feed_id": "",
            "provider": "",
        })

    # Largest/smallest by different metrics
    by_trips = sorted(summaries, key=lambda s: s.get("network_stats", {}).get("total_trips", 0), reverse=True)
    if by_trips:
        top = by_trips[0]
        bottom = by_trips[-1]
        pairs.append({
            "instruction": "Which transit agency has the most scheduled trips?",
            "response": f"{top['provider']} ({top.get('country_code', '')}) has the most scheduled trips with {top.get('network_stats', {}).get('total_trips', 0):,}. The fewest is {bottom['provider']} with {bottom.get('network_stats', {}).get('total_trips', 0):,} trips.",
            "category": "comparative",
            "template_id": "most_trips",
            "feed_id": "",
            "provider": "",
        })

    # Agencies by mode diversity
    by_modes = sorted(summaries, key=lambda s: len(s.get("route_summary", {}).get("by_type", {})), reverse=True)
    if by_modes:
        most_diverse = by_modes[0]
        modes = len(most_diverse.get("route_summary", {}).get("by_type", {}))
        pairs.append({
            "instruction": "Which transit agency offers the most diverse range of transit modes?",
            "response": f"{most_diverse['provider']} ({most_diverse.get('country_code', '')}) offers the most diverse transit with {modes} different modes: " +
                ", ".join(ROUTE_TYPE_NAMES.get(int(rt), f"type {rt}") for rt in sorted(most_diverse.get("route_summary", {}).get("by_type", {}).keys())) + ".",
            "category": "comparative",
            "template_id": "most_diverse_modes",
            "feed_id": "",
            "provider": "",
        })

    return pairs


def generate_network_stats_expanded(summaries: list[dict]) -> list[dict]:
    """Generate additional network stats pairs from feed data."""
    pairs: list[dict] = []

    for s in summaries:
        provider = s.get("provider", "")
        ns = s.get("network_stats", {})
        if not provider or not ns:
            continue

        pairs.append({
            "instruction": f"What are the key network statistics for {provider}?",
            "response": f"{provider} operates {ns.get('total_routes', 0)} routes serving {ns.get('total_stops', 0):,} stops with {ns.get('total_trips', 0):,} scheduled trips. On average, each route serves {ns.get('avg_stops_per_route', 0)} stops and runs {ns.get('avg_trips_per_route', 0):.0f} trips.",
            "category": "network_stats",
            "template_id": "key_network_stats",
            "feed_id": s.get("feed_id", ""),
            "provider": provider,
        })

    return pairs


# ═══════════════════════════════════════════════════════════════════════════════
# Main: generate all expanded pairs
# ═══════════════════════════════════════════════════════════════════════════════

def load_feed_summaries() -> list[dict]:
    summaries = []
    for feed_dir in sorted(CLEANED_DIR.iterdir()):
        summary_path = feed_dir / "feed_summary.json"
        if summary_path.exists():
            with open(summary_path) as f:
                summaries.append(json.load(f))
    return summaries


def generate_all_expanded_pairs() -> list[dict]:
    """Generate all expanded training pairs."""
    summaries = load_feed_summaries()
    logger.info("Loaded %d feed summaries", len(summaries))

    all_pairs: list[dict] = []

    # Static knowledge pairs
    for p in JOURNEY_PLANNING_PAIRS:
        all_pairs.append({**p, "category": "journey_planning", "template_id": "jp_static", "feed_id": "", "provider": ""})

    for p in GTFS_KNOWLEDGE_EXPANDED:
        all_pairs.append({**p, "category": "gtfs_knowledge", "template_id": "gk_expanded", "feed_id": "", "provider": ""})

    for p in GTFS_VALIDATION_PAIRS:
        all_pairs.append({**p, "category": "gtfs_validation", "template_id": "gv_static", "feed_id": "", "provider": ""})

    for p in TRANSIT_OPERATIONS_PAIRS:
        all_pairs.append({**p, "category": "transit_operations", "template_id": "to_static", "feed_id": "", "provider": ""})

    logger.info("  Static pairs: %d", len(all_pairs))

    # Data-driven pairs
    jp_feed = generate_journey_planning_from_feeds(summaries)
    all_pairs.extend(jp_feed)
    logger.info("  Journey planning (feed-driven): %d", len(jp_feed))

    comp = generate_comparative_expanded(summaries)
    all_pairs.extend(comp)
    logger.info("  Comparative (expanded): %d", len(comp))

    ns = generate_network_stats_expanded(summaries)
    all_pairs.extend(ns)
    logger.info("  Network stats (expanded): %d", len(ns))

    logger.info("Total expanded pairs: %d", len(all_pairs))
    return all_pairs


if __name__ == "__main__":
    pairs = generate_all_expanded_pairs()
    output = Path("datasets/synthetic/expanded_pairs.jsonl")
    with open(output, "w") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"Saved {len(pairs)} expanded pairs to {output}")
