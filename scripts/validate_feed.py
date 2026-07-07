"""Basic GTFS ZIP validation using stdlib only."""

import csv
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from scripts.config import get_logger

logger = get_logger(__name__)

# GTFS required files — at least one of calendar.txt or calendar_dates.txt must exist
REQUIRED_FILES = {"agency.txt", "routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}
CALENDAR_FILES = {"calendar.txt", "calendar_dates.txt"}


@dataclass
class FeedValidationResult:
    """Result of validating a GTFS ZIP file."""

    is_valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    file_count: int = 0
    files_found: list[str] = field(default_factory=list)
    total_size_bytes: int = 0


def validate_gtfs_zip(zip_path: Path) -> FeedValidationResult:
    """Validate a GTFS ZIP file for basic structural correctness.

    Checks:
    - File is a valid ZIP archive
    - Required GTFS files are present and non-empty
    - At least one of calendar.txt or calendar_dates.txt exists
    - Required CSV files have parseable headers
    """
    result = FeedValidationResult()

    # Check ZIP is valid
    if not zip_path.exists():
        result.errors.append(f"File not found: {zip_path}")
        return result

    if not zipfile.is_zipfile(zip_path):
        result.errors.append(f"Not a valid ZIP file: {zip_path}")
        return result

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Get all file names, handling files in subdirectories
            all_names = zf.namelist()
            # Normalize: strip leading directory if files are nested
            basenames = {Path(name).name for name in all_names if not name.endswith("/")}

            result.file_count = len(basenames)
            result.files_found = sorted(basenames)
            result.total_size_bytes = sum(info.file_size for info in zf.infolist())

            # Check required files
            missing = REQUIRED_FILES - basenames
            if missing:
                result.errors.append(f"Missing required files: {', '.join(sorted(missing))}")

            # Check calendar — need at least one
            if not (CALENDAR_FILES & basenames):
                result.errors.append(
                    "Missing both calendar.txt and calendar_dates.txt (need at least one)"
                )

            # Check that required files are non-empty and have valid CSV headers
            files_to_check = (REQUIRED_FILES | CALENDAR_FILES) & basenames
            for filename in files_to_check:
                # Find the actual path in the ZIP (may be in a subdirectory)
                actual_path = _find_in_zip(all_names, filename)
                if actual_path is None:
                    continue

                try:
                    data = zf.read(actual_path)
                    if len(data) == 0:
                        result.errors.append(f"{filename} is empty")
                        continue

                    # Try to parse CSV header
                    text = data.decode("utf-8-sig")  # Handle BOM
                    reader = csv.reader(io.StringIO(text))
                    header = next(reader, None)
                    if header is None or len(header) == 0:
                        result.warnings.append(f"{filename} has no CSV header")

                except (UnicodeDecodeError, csv.Error) as e:
                    result.warnings.append(f"{filename} encoding/parse issue: {e}")

    except zipfile.BadZipFile as e:
        result.errors.append(f"Corrupted ZIP file: {e}")
        return result

    result.is_valid = len(result.errors) == 0
    return result


def _find_in_zip(names: list[str], filename: str) -> str | None:
    """Find a file in the ZIP, even if it's nested in a subdirectory."""
    for name in names:
        if Path(name).name == filename:
            return name
    return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m scripts.validate_feed <path-to-gtfs.zip>")
        sys.exit(1)

    path = Path(sys.argv[1])
    result = validate_gtfs_zip(path)

    print(f"\nValidation: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"Files found ({result.file_count}): {', '.join(result.files_found)}")
    print(f"Total size: {result.total_size_bytes:,} bytes")

    if result.errors:
        print(f"\nErrors:")
        for err in result.errors:
            print(f"  ✗ {err}")
    if result.warnings:
        print(f"\nWarnings:")
        for warn in result.warnings:
            print(f"  ! {warn}")
