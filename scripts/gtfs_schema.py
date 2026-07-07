"""Canonical GTFS schema definitions for data cleaning.

Defines the expected columns, dtypes, and primary keys for each GTFS file type
based on the official GTFS specification. Non-spec columns from agency-specific
extensions are dropped during cleaning.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GtfsFileSpec:
    """Schema specification for one GTFS file type."""

    filename: str
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...] = ()
    primary_key: tuple[str, ...] = ()
    dtypes: dict[str, str] = field(default_factory=dict)
    is_required_file: bool = False  # Must exist in a valid GTFS feed
    chunk_threshold_bytes: int = 100_000_000  # 100 MB

    @property
    def all_columns(self) -> tuple[str, ...]:
        return self.required_columns + self.optional_columns

    @property
    def parquet_name(self) -> str:
        return self.filename.replace(".txt", ".parquet")


GTFS_SCHEMAS: dict[str, GtfsFileSpec] = {
    "agency.txt": GtfsFileSpec(
        filename="agency.txt",
        is_required_file=True,
        required_columns=(
            "agency_id", "agency_name", "agency_url", "agency_timezone",
        ),
        optional_columns=(
            "agency_lang", "agency_phone", "agency_fare_url", "agency_email",
        ),
        primary_key=("agency_id",),
        dtypes={
            "agency_id": "str",
            "agency_name": "str",
            "agency_url": "str",
            "agency_timezone": "str",
            "agency_lang": "str",
            "agency_phone": "str",
            "agency_fare_url": "str",
            "agency_email": "str",
        },
    ),
    "routes.txt": GtfsFileSpec(
        filename="routes.txt",
        is_required_file=True,
        required_columns=(
            "route_id", "route_short_name", "route_long_name", "route_type",
        ),
        optional_columns=(
            "agency_id", "route_desc", "route_url", "route_color",
            "route_text_color", "route_sort_order",
        ),
        primary_key=("route_id",),
        dtypes={
            "route_id": "str",
            "agency_id": "str",
            "route_short_name": "str",
            "route_long_name": "str",
            "route_desc": "str",
            "route_type": "Int16",
            "route_url": "str",
            "route_color": "str",
            "route_text_color": "str",
            "route_sort_order": "Int32",
        },
    ),
    "trips.txt": GtfsFileSpec(
        filename="trips.txt",
        is_required_file=True,
        required_columns=(
            "route_id", "service_id", "trip_id",
        ),
        optional_columns=(
            "trip_headsign", "trip_short_name", "direction_id", "block_id",
            "shape_id", "wheelchair_accessible", "bikes_allowed",
        ),
        primary_key=("trip_id",),
        dtypes={
            "route_id": "str",
            "service_id": "str",
            "trip_id": "str",
            "trip_headsign": "str",
            "trip_short_name": "str",
            "direction_id": "Int8",
            "block_id": "str",
            "shape_id": "str",
            "wheelchair_accessible": "Int8",
            "bikes_allowed": "Int8",
        },
    ),
    "stops.txt": GtfsFileSpec(
        filename="stops.txt",
        is_required_file=True,
        required_columns=(
            "stop_id", "stop_name", "stop_lat", "stop_lon",
        ),
        optional_columns=(
            "stop_code", "stop_desc", "zone_id", "stop_url", "location_type",
            "parent_station", "stop_timezone", "wheelchair_boarding",
            "platform_code",
        ),
        primary_key=("stop_id",),
        dtypes={
            "stop_id": "str",
            "stop_code": "str",
            "stop_name": "str",
            "stop_desc": "str",
            "stop_lat": "float64",
            "stop_lon": "float64",
            "zone_id": "str",
            "stop_url": "str",
            "location_type": "Int8",
            "parent_station": "str",
            "stop_timezone": "str",
            "wheelchair_boarding": "Int8",
            "platform_code": "str",
        },
    ),
    "stop_times.txt": GtfsFileSpec(
        filename="stop_times.txt",
        is_required_file=True,
        required_columns=(
            "trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence",
        ),
        optional_columns=(
            "stop_headsign", "pickup_type", "drop_off_type",
            "shape_dist_traveled", "timepoint",
        ),
        primary_key=("trip_id", "stop_sequence"),
        dtypes={
            "trip_id": "str",
            "arrival_time": "str",  # Keep as string — GTFS allows >24:00:00
            "departure_time": "str",
            "stop_id": "str",
            "stop_sequence": "Int32",
            "stop_headsign": "str",
            "pickup_type": "Int8",
            "drop_off_type": "Int8",
            "shape_dist_traveled": "float64",
            "timepoint": "Int8",
        },
    ),
    "calendar.txt": GtfsFileSpec(
        filename="calendar.txt",
        is_required_file=False,
        required_columns=(
            "service_id", "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday", "start_date", "end_date",
        ),
        primary_key=("service_id",),
        dtypes={
            "service_id": "str",
            "monday": "Int8",
            "tuesday": "Int8",
            "wednesday": "Int8",
            "thursday": "Int8",
            "friday": "Int8",
            "saturday": "Int8",
            "sunday": "Int8",
            "start_date": "str",
            "end_date": "str",
        },
    ),
    "calendar_dates.txt": GtfsFileSpec(
        filename="calendar_dates.txt",
        is_required_file=False,
        required_columns=(
            "service_id", "date", "exception_type",
        ),
        primary_key=("service_id", "date"),
        dtypes={
            "service_id": "str",
            "date": "str",
            "exception_type": "Int8",
        },
    ),
    "shapes.txt": GtfsFileSpec(
        filename="shapes.txt",
        is_required_file=False,
        required_columns=(
            "shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence",
        ),
        optional_columns=(
            "shape_dist_traveled",
        ),
        primary_key=("shape_id", "shape_pt_sequence"),
        dtypes={
            "shape_id": "str",
            "shape_pt_lat": "float64",
            "shape_pt_lon": "float64",
            "shape_pt_sequence": "Int32",
            "shape_dist_traveled": "float64",
        },
    ),
    "transfers.txt": GtfsFileSpec(
        filename="transfers.txt",
        is_required_file=False,
        required_columns=(
            "from_stop_id", "to_stop_id",
        ),
        optional_columns=(
            "transfer_type", "min_transfer_time",
        ),
        primary_key=("from_stop_id", "to_stop_id"),
        dtypes={
            "from_stop_id": "str",
            "to_stop_id": "str",
            "transfer_type": "Int8",
            "min_transfer_time": "Int32",
        },
    ),
    "frequencies.txt": GtfsFileSpec(
        filename="frequencies.txt",
        is_required_file=False,
        required_columns=(
            "trip_id", "start_time", "end_time", "headway_secs",
        ),
        optional_columns=(
            "exact_times",
        ),
        primary_key=("trip_id", "start_time"),
        dtypes={
            "trip_id": "str",
            "start_time": "str",
            "end_time": "str",
            "headway_secs": "Int32",
            "exact_times": "Int8",
        },
    ),
    "feed_info.txt": GtfsFileSpec(
        filename="feed_info.txt",
        is_required_file=False,
        required_columns=(
            "feed_publisher_name", "feed_publisher_url", "feed_lang",
        ),
        optional_columns=(
            "feed_start_date", "feed_end_date", "feed_version",
            "feed_contact_email", "feed_contact_url", "default_lang",
        ),
        primary_key=(),
        dtypes={
            "feed_publisher_name": "str",
            "feed_publisher_url": "str",
            "feed_lang": "str",
            "feed_start_date": "str",
            "feed_end_date": "str",
            "feed_version": "str",
            "feed_contact_email": "str",
            "feed_contact_url": "str",
            "default_lang": "str",
        },
    ),
}
