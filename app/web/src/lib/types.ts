export interface FeedValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  file_count: number;
  files_found: string[];
  total_size_bytes: number;
}

export interface AgencyInfo {
  agency_id: string;
  agency_name: string;
  agency_url: string;
  agency_timezone: string;
}

export interface RouteDetail {
  route_id: string;
  route_short_name: string;
  route_long_name: string;
  route_type: number;
  trip_count?: number;
  stop_count?: number;
  first_departure?: string;
  last_departure?: string;
  headsigns?: string[];
}

export interface RouteSummary {
  total_routes: number;
  by_type: Record<string, number>;
  routes: RouteDetail[];
}

export interface StopSummary {
  total_stops: number;
  by_location_type: Record<string, number>;
  sample_stops: { stop_id: string; stop_name: string; stop_lat: string; stop_lon: string }[];
}

export interface CalendarSummary {
  weekday_services: number;
  weekend_services: number;
  date_range: string[];
  calendar_dates_count: number;
}

export interface TransferSummary {
  total_transfers: number;
  sample_transfers: {
    from_stop_name: string;
    to_stop_name: string;
    transfer_type: number | null;
    min_transfer_time: number | null;
  }[];
}

export interface NetworkStats {
  total_routes: number;
  total_stops: number;
  total_trips: number;
  avg_stops_per_route: number;
  avg_trips_per_route: number;
}

export interface FeedSummary {
  agency: AgencyInfo[];
  route_summary: RouteSummary;
  stop_summary: StopSummary;
  calendar_summary: CalendarSummary;
  transfer_summary: TransferSummary;
  network_stats: NetworkStats;
}

export interface FeedUploadResponse {
  upload_id: string | null;
  validation: FeedValidation;
  summary: FeedSummary | null;
}

export interface ChatResponse {
  answer: string;
  tokens: number;
  time_seconds: number;
}

export const ROUTE_TYPE_NAMES: Record<number, string> = {
  0: "Tram/Light Rail",
  1: "Subway/Metro",
  2: "Rail",
  3: "Bus",
  4: "Ferry",
  5: "Cable Tram",
  6: "Gondola",
  7: "Funicular",
  11: "Trolleybus",
  12: "Monorail",
};
