"""Download GTFS feeds from the seed list with provenance tracking."""

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
from tqdm import tqdm

from scripts.config import (
    CHUNK_SIZE,
    MAX_RETRIES,
    RAW_DIR,
    REQUEST_TIMEOUT,
    RETRY_DELAY,
    SEED_FEEDS_PATH,
    USER_AGENT,
    get_logger,
)
from scripts.validate_feed import validate_gtfs_zip

logger = get_logger(__name__)


@dataclass
class DownloadResult:
    """Result of downloading a single GTFS feed."""

    feed_id: str
    provider: str
    success: bool
    skipped: bool = False
    error: str | None = None
    duration_seconds: float = 0.0
    file_size_bytes: int = 0


def load_seed_feeds(path: Path | None = None) -> list[dict]:
    """Load the seed feeds list from JSON."""
    feed_path = path or SEED_FEEDS_PATH

    if not feed_path.exists():
        raise FileNotFoundError(
            f"Seed feeds not found at {feed_path}. Run feed_selector.py first."
        )

    with open(feed_path, encoding="utf-8") as f:
        feeds = json.load(f)

    logger.info("Loaded %d seed feeds from %s", len(feeds), feed_path)
    return feeds


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_feed(feed: dict, output_dir: Path | None = None) -> DownloadResult:
    """Download a single GTFS feed with retry logic.

    Creates a directory per feed containing:
    - gtfs.zip: The GTFS feed archive
    - metadata.json: Provenance and validation info
    """
    out = output_dir or RAW_DIR
    feed_id = str(feed["feed_id"])
    provider = feed.get("provider", "Unknown")
    download_url = feed["download_url"]

    feed_dir = out / f"mdb-{feed_id}"
    zip_path = feed_dir / "gtfs.zip"
    metadata_path = feed_dir / "metadata.json"

    # Skip if already downloaded and valid
    if zip_path.exists():
        logger.info("[%s] Already downloaded, skipping: %s", feed_id, provider)
        return DownloadResult(
            feed_id=feed_id, provider=provider, success=True, skipped=True
        )

    feed_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.time()

    # Download with retries
    last_error: str | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "[%s] Downloading %s (attempt %d/%d)",
                feed_id, provider, attempt, MAX_RETRIES,
            )

            response = requests.get(
                download_url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
                stream=True,
            )
            response.raise_for_status()

            # Stream to file with progress bar
            total = int(response.headers.get("content-length", 0))
            with open(zip_path, "wb") as f:
                with tqdm(
                    total=total or None,
                    unit="B",
                    unit_scale=True,
                    desc=f"mdb-{feed_id}",
                    leave=False,
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        f.write(chunk)
                        pbar.update(len(chunk))

            # Validate the downloaded file
            validation = validate_gtfs_zip(zip_path)
            duration = time.time() - start_time
            file_size = zip_path.stat().st_size

            if not validation.is_valid:
                logger.warning(
                    "[%s] Downloaded but validation failed: %s",
                    feed_id, "; ".join(validation.errors),
                )

            # Write provenance metadata
            metadata = {
                "feed_id": feed_id,
                "provider": provider,
                "download_url": download_url,
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "file_size_bytes": file_size,
                "sha256": _compute_sha256(zip_path),
                "license_url": feed.get("license_url", ""),
                "country_code": feed.get("country_code", ""),
                "category": feed.get("category", ""),
                "source": "mobility_database",
                "validation": {
                    "is_valid": validation.is_valid,
                    "file_count": validation.file_count,
                    "files_found": validation.files_found,
                    "total_size_bytes": validation.total_size_bytes,
                    "errors": validation.errors,
                    "warnings": validation.warnings,
                },
                "umartransit_version": "0.1.0",
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(
                "[%s] Done: %s (%s bytes, %.1fs, valid=%s)",
                feed_id, provider, f"{file_size:,}", duration, validation.is_valid,
            )

            return DownloadResult(
                feed_id=feed_id,
                provider=provider,
                success=True,
                duration_seconds=duration,
                file_size_bytes=file_size,
            )

        except requests.RequestException as e:
            last_error = str(e)
            logger.warning("[%s] Attempt %d failed: %s", feed_id, attempt, last_error)

            # Clean up partial download
            if zip_path.exists():
                zip_path.unlink()

            if attempt < MAX_RETRIES:
                delay = RETRY_DELAY * (2 ** (attempt - 1))  # Exponential backoff
                logger.info("[%s] Retrying in %.1f seconds...", feed_id, delay)
                time.sleep(delay)

    # All retries exhausted
    duration = time.time() - start_time
    logger.error("[%s] Failed after %d attempts: %s", feed_id, MAX_RETRIES, last_error)
    return DownloadResult(
        feed_id=feed_id,
        provider=provider,
        success=False,
        error=last_error,
        duration_seconds=duration,
    )


def download_all_feeds(
    feeds: list[dict],
    output_dir: Path | None = None,
) -> list[DownloadResult]:
    """Download all seed feeds sequentially."""
    out = output_dir or RAW_DIR
    out.mkdir(parents=True, exist_ok=True)

    results: list[DownloadResult] = []
    total = len(feeds)

    print(f"\nDownloading {total} GTFS feeds to {out}\n")

    for i, feed in enumerate(feeds, 1):
        print(f"[{i}/{total}] {feed.get('provider', 'Unknown')} ({feed.get('country_code', '')})")
        result = download_feed(feed, out)
        results.append(result)

        # Be polite — small delay between downloads
        if i < total and not result.skipped:
            time.sleep(1.0)

    return results


def print_summary(results: list[DownloadResult]) -> None:
    """Print download summary."""
    succeeded = [r for r in results if r.success and not r.skipped]
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if not r.success]

    total_bytes = sum(r.file_size_bytes for r in succeeded)
    total_time = sum(r.duration_seconds for r in succeeded)

    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)
    print(f"  Downloaded: {len(succeeded)}")
    print(f"  Skipped:    {len(skipped)} (already existed)")
    print(f"  Failed:     {len(failed)}")
    print(f"  Total size: {total_bytes / 1024 / 1024:.1f} MB")
    print(f"  Total time: {total_time:.1f}s")

    if failed:
        print("\nFailed feeds:")
        for r in failed:
            print(f"  - {r.provider} ({r.feed_id}): {r.error}")


def main() -> None:
    """Entry point: download all seed feeds."""
    feeds = load_seed_feeds()
    results = download_all_feeds(feeds)
    print_summary(results)


if __name__ == "__main__":
    main()
