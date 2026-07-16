import type { FeedSummary, FeedValidation } from "./types";

export const DEMO_FEED_VALIDATION: FeedValidation = {
  is_valid: true,
  errors: [],
  warnings: [],
  file_count: 10,
  files_found: [
    "agency.txt", "calendar.txt", "calendar_dates.txt", "routes.txt",
    "shapes.txt", "stop_times.txt", "stops.txt", "transfers.txt", "trips.txt",
  ],
  total_size_bytes: 185_000_000,
};

export const DEMO_FEED_SUMMARY: FeedSummary = {
  agency: [{
    agency_id: "50066",
    agency_name: "Chicago Transit Authority",
    agency_url: "http://transitchicago.com",
    agency_timezone: "America/Chicago",
  }],
  route_summary: {
    total_routes: 133,
    by_type: { "3": 125, "1": 8 },
    routes: [
      { route_id: "Red", route_short_name: "Red", route_long_name: "Red Line", route_type: 1, trip_count: 1200, stop_count: 33, first_departure: "04:30:00", last_departure: "25:15:00", headsigns: ["95th/Dan Ryan", "Howard"] },
      { route_id: "Blue", route_short_name: "Blue", route_long_name: "Blue Line", route_type: 1, trip_count: 1100, stop_count: 33, first_departure: "00:00:00", last_departure: "23:59:00", headsigns: ["O'Hare", "Forest Park"] },
      { route_id: "Brown", route_short_name: "Brown", route_long_name: "Brown Line", route_type: 1, trip_count: 800, stop_count: 27, first_departure: "04:25:00", last_departure: "25:00:00", headsigns: ["Kimball", "Loop"] },
      { route_id: "1", route_short_name: "1", route_long_name: "Bronzeville/Union Station", route_type: 3, trip_count: 118, stop_count: 67, first_departure: "05:45:00", last_departure: "18:56:30", headsigns: [] },
      { route_id: "3", route_short_name: "3", route_long_name: "King Drive", route_type: 3, trip_count: 1169, stop_count: 216, first_departure: "00:08:28", last_departure: "23:58:28", headsigns: [] },
      { route_id: "4", route_short_name: "4", route_long_name: "Cottage Grove", route_type: 3, trip_count: 1466, stop_count: 254, first_departure: "00:10:00", last_departure: "23:59:30", headsigns: [] },
      { route_id: "9", route_short_name: "9", route_long_name: "Ashland", route_type: 3, trip_count: 1808, stop_count: 240, first_departure: "00:00:00", last_departure: "23:59:00", headsigns: [] },
      { route_id: "8", route_short_name: "8", route_long_name: "Halsted", route_type: 3, trip_count: 1178, stop_count: 211, first_departure: "00:05:00", last_departure: "23:59:30", headsigns: [] },
      { route_id: "6", route_short_name: "6", route_long_name: "Jackson Park Express", route_type: 3, trip_count: 1122, stop_count: 117, first_departure: "00:00:30", last_departure: "23:56:30", headsigns: [] },
      { route_id: "12", route_short_name: "12", route_long_name: "Roosevelt", route_type: 3, trip_count: 1428, stop_count: 125, first_departure: "00:00:00", last_departure: "23:54:00", headsigns: [] },
    ],
  },
  stop_summary: {
    total_stops: 11177,
    by_location_type: { "0": 11020, "1": 143, "2": 14 },
    sample_stops: [],
  },
  calendar_summary: {
    weekday_services: 115,
    weekend_services: 39,
    date_range: ["20260528", "20260731"],
    calendar_dates_count: 85,
  },
  transfer_summary: {
    total_transfers: 153,
    sample_transfers: [
      { from_stop_name: "Racine", to_stop_name: "Racine", transfer_type: 0, min_transfer_time: null },
      { from_stop_name: "Merchandise Mart", to_stop_name: "Merchandise Mart", transfer_type: 0, min_transfer_time: null },
      { from_stop_name: "Roosevelt (Elevated)", to_stop_name: "Roosevelt (Subway)", transfer_type: 0, min_transfer_time: null },
    ],
  },
  network_stats: {
    total_routes: 133,
    total_stops: 11177,
    total_trips: 37802,
    avg_stops_per_route: 84.0,
    avg_trips_per_route: 284.2,
  },
};

export const DEMO_FEED_QA: Record<string, string> = {
  "How many routes does this agency operate?":
    "Chicago Transit Authority operates 133 routes: 125 Bus routes and 8 Subway/Metro routes (including the Red, Blue, Brown, Green, Orange, Pink, Purple, and Yellow lines).",
  "What is the busiest route?":
    "Route 9 (Ashland) is the busiest with 1,808 scheduled trips, serving 240 stops. It runs nearly 24 hours from 00:00 to 23:59.",
  "Which routes run on weekends?":
    "The feed defines 39 weekend service patterns out of 115 weekday patterns, indicating reduced weekend service. The Blue Line runs 24/7, and most major bus routes have weekend schedules.",
  "How many stops are in the network?":
    "The CTA network has 11,177 stops total. Of these, 143 are classified as stations (location_type=1) and 14 as entrances/exits (location_type=2). The remaining 11,020 are regular bus stops.",
  "What transit modes are available?":
    "CTA operates two transit modes: Bus service (125 routes) and Subway/Metro service (8 routes — the Red, Blue, Brown, Green, Orange, Pink, Purple, and Yellow lines).",
  "What is the service date range?":
    "The current schedule covers May 28, 2026 to July 31, 2026 with 85 calendar date exceptions defined.",
};

export const DEMO_FEED_EXAMPLES = [
  "How many routes does this agency operate?",
  "What is the busiest route?",
  "Which routes run on weekends?",
  "How many stops are in the network?",
  "What transit modes are available?",
];
