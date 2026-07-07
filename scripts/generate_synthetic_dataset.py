"""Stage 2: Generate synthetic instruction/response dataset from feed summaries."""

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from scripts.config import CLEANED_DIR, SYNTHETIC_DIR, get_logger
from scripts.question_templates import (
    ALL_TEMPLATES,
    GTFS_KNOWLEDGE_PAIRS,
    ROUTE_TYPE_NAMES,
    generate_comparative_pairs,
)

logger = get_logger(__name__)

MAX_ROUTES_PER_FEED = 15  # Sample top + random routes per feed for detailed Q&A
MAX_STOPS_PER_FEED = 30  # Sample stops for location Q&A
MAX_TRANSFERS_PER_FEED = 15  # Sample transfers for Q&A


def load_feed_summaries(cleaned_dir: Path | None = None) -> list[dict]:
    """Load all feed_summary.json files from cleaned directories."""
    cdir = cleaned_dir or CLEANED_DIR
    summaries = []

    for feed_dir in sorted(cdir.iterdir()):
        if not feed_dir.is_dir() or not feed_dir.name.startswith("mdb-"):
            continue
        summary_path = feed_dir / "feed_summary.json"
        if summary_path.exists():
            with open(summary_path, encoding="utf-8") as f:
                summaries.append(json.load(f))

    logger.info("Loaded %d feed summaries", len(summaries))
    return summaries


def _select_routes(summary: dict, rng: random.Random) -> list[dict]:
    """Select a diverse set of routes from a feed summary for Q&A."""
    routes = summary.get("route_summary", {}).get("routes", [])
    if not routes:
        return []

    # Sort by trip_count descending (busiest first)
    with_trips = [r for r in routes if r.get("trip_count", 0) > 0]
    with_trips.sort(key=lambda r: r.get("trip_count", 0), reverse=True)

    # Take top routes by trip count
    top_n = min(MAX_ROUTES_PER_FEED // 2, len(with_trips))
    selected = with_trips[:top_n]

    # Add random routes for diversity
    remaining = [r for r in with_trips[top_n:]]
    random_n = min(MAX_ROUTES_PER_FEED - top_n, len(remaining))
    if random_n > 0:
        selected.extend(rng.sample(remaining, random_n))

    return selected


def generate_data_driven_pairs(summaries: list[dict], rng: random.Random) -> list[dict]:
    """Generate instruction/response pairs from feed summaries using templates."""
    pairs: list[dict] = []

    for summary in summaries:
        feed_id = summary.get("feed_id", "")
        provider = summary.get("provider", "")
        country = summary.get("country_code", "")
        by_type = summary.get("route_summary", {}).get("by_type", {})
        net_stats = summary.get("network_stats", {})

        # ── Agency Overview (Category 1) ──
        for agency in summary.get("agency", []):
            agency_facts = {
                "agency_name": agency.get("agency_name", provider),
                "agency_timezone": agency.get("agency_timezone", ""),
                "by_type": by_type,
                "total_routes": summary.get("route_summary", {}).get("total_routes", 0),
                "total_stops": summary.get("stop_summary", {}).get("total_stops", 0),
                "total_trips": net_stats.get("total_trips", 0),
            }
            for tmpl in ALL_TEMPLATES:
                if tmpl.category == "agency_overview":
                    pair = tmpl.generate(agency_facts)
                    if pair:
                        pairs.append({
                            **pair,
                            "category": tmpl.category,
                            "template_id": tmpl.template_id,
                            "feed_id": feed_id,
                            "provider": provider,
                        })

        # ── Route Information (Category 2) & Schedule (Category 4) ──
        selected_routes = _select_routes(summary, rng)
        for route in selected_routes:
            route_facts = {
                **route,
                "provider": provider,
            }
            for tmpl in ALL_TEMPLATES:
                if tmpl.category in ("route_info", "schedule"):
                    if tmpl.template_id == "route_list_by_type":
                        continue  # Handled separately below
                    pair = tmpl.generate(route_facts)
                    if pair:
                        pairs.append({
                            **pair,
                            "category": tmpl.category,
                            "template_id": tmpl.template_id,
                            "feed_id": feed_id,
                            "provider": provider,
                        })

        # Route list by type (one per route_type per feed)
        all_routes = summary.get("route_summary", {}).get("routes", [])
        for rt in by_type:
            routes_of_type = [r for r in all_routes if r.get("route_type") == int(rt)]
            if routes_of_type:
                type_facts = {
                    "provider": provider,
                    "route_type_filter": int(rt),
                    "routes_of_type": routes_of_type,
                }
                for tmpl in ALL_TEMPLATES:
                    if tmpl.template_id == "route_list_by_type":
                        pair = tmpl.generate(type_facts)
                        if pair:
                            pairs.append({
                                **pair,
                                "category": tmpl.category,
                                "template_id": tmpl.template_id,
                                "feed_id": feed_id,
                                "provider": provider,
                            })

        # ── Stop Information (Category 3) ──
        sample_stops = summary.get("stop_summary", {}).get("sample_stops", [])
        stop_sample = rng.sample(sample_stops, min(MAX_STOPS_PER_FEED, len(sample_stops)))
        for stop in stop_sample:
            stop_facts = {**stop, "provider": provider}
            for tmpl in ALL_TEMPLATES:
                if tmpl.category == "stop_info" and tmpl.template_id.startswith("stop_location"):
                    pair = tmpl.generate(stop_facts)
                    if pair:
                        pairs.append({
                            **pair,
                            "category": tmpl.category,
                            "template_id": tmpl.template_id,
                            "feed_id": feed_id,
                            "provider": provider,
                        })

        # Stop count (once per feed)
        stop_facts = {
            "provider": provider,
            "total_stops": summary.get("stop_summary", {}).get("total_stops", 0),
            "station_count": len(summary.get("stop_summary", {}).get("stations", [])),
        }
        for tmpl in ALL_TEMPLATES:
            if tmpl.template_id == "stop_count":
                pair = tmpl.generate(stop_facts)
                if pair:
                    pairs.append({
                        **pair,
                        "category": tmpl.category,
                        "template_id": tmpl.template_id,
                        "feed_id": feed_id,
                        "provider": provider,
                    })

        # ── Transfer Analysis (Category 5) ──
        transfers = summary.get("transfer_summary", {}).get("sample_transfers", [])
        transfer_sample = rng.sample(transfers, min(MAX_TRANSFERS_PER_FEED, len(transfers)))
        for transfer in transfer_sample:
            transfer_facts = {**transfer, "provider": provider}
            for tmpl in ALL_TEMPLATES:
                if tmpl.template_id == "transfer_info":
                    pair = tmpl.generate(transfer_facts)
                    if pair:
                        pairs.append({
                            **pair,
                            "category": tmpl.category,
                            "template_id": tmpl.template_id,
                            "feed_id": feed_id,
                            "provider": provider,
                        })

        # Transfer count (once per feed)
        transfer_count_facts = {
            "provider": provider,
            "total_transfers": summary.get("transfer_summary", {}).get("total_transfers", 0),
        }
        for tmpl in ALL_TEMPLATES:
            if tmpl.template_id == "transfer_count":
                pair = tmpl.generate(transfer_count_facts)
                if pair:
                    pairs.append({
                        **pair,
                        "category": tmpl.category,
                        "template_id": tmpl.template_id,
                        "feed_id": feed_id,
                        "provider": provider,
                    })

        # ── Network Statistics (Category 6) ──
        network_facts = {
            "provider": provider,
            "country_code": country,
            "network_stats": net_stats,
        }
        for tmpl in ALL_TEMPLATES:
            if tmpl.category == "network_stats":
                pair = tmpl.generate(network_facts)
                if pair:
                    pairs.append({
                        **pair,
                        "category": tmpl.category,
                        "template_id": tmpl.template_id,
                        "feed_id": feed_id,
                        "provider": provider,
                    })

    return pairs


def deduplicate_pairs(pairs: list[dict]) -> list[dict]:
    """Remove exact-duplicate instructions."""
    seen: set[str] = set()
    unique = []
    for pair in pairs:
        key = pair["instruction"]
        if key not in seen:
            seen.add(key)
            unique.append(pair)
    removed = len(pairs) - len(unique)
    if removed > 0:
        logger.info("Removed %d duplicate instructions", removed)
    return unique


def write_jsonl(pairs: list[dict], output_path: Path) -> None:
    """Write pairs to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
    logger.info("Wrote %d pairs to %s", len(pairs), output_path)


def write_report(pairs: list[dict], output_dir: Path) -> Path:
    """Write generation report with category counts."""
    report_path = output_dir / "generation_report.json"

    category_counts: dict[str, int] = {}
    feed_counts: dict[str, int] = {}
    template_counts: dict[str, int] = {}

    for pair in pairs:
        cat = pair.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        fid = pair.get("feed_id", "")
        if fid:
            feed_counts[fid] = feed_counts.get(fid, 0) + 1
        tid = pair.get("template_id", "")
        template_counts[tid] = template_counts.get(tid, 0) + 1

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pairs": len(pairs),
        "category_counts": dict(sorted(category_counts.items())),
        "feed_counts": dict(sorted(feed_counts.items())),
        "template_counts": dict(sorted(template_counts.items())),
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("Report saved to %s", report_path)
    return report_path


def main() -> None:
    """Entry point: generate synthetic dataset."""
    parser = argparse.ArgumentParser(description="Generate synthetic Q&A dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--cleaned-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out_dir = args.output_dir or SYNTHETIC_DIR

    # Load summaries
    summaries = load_feed_summaries(args.cleaned_dir)
    if not summaries:
        logger.error("No feed summaries found. Run precompute_feed_stats.py first.")
        raise SystemExit(1)

    # Generate data-driven pairs (categories 1-6)
    logger.info("Generating data-driven pairs...")
    data_pairs = generate_data_driven_pairs(summaries, rng)
    logger.info("Generated %d data-driven pairs", len(data_pairs))

    # Add GTFS knowledge pairs (category 7)
    knowledge_pairs = GTFS_KNOWLEDGE_PAIRS.copy()
    for p in knowledge_pairs:
        p.setdefault("feed_id", "")
        p.setdefault("provider", "")
    logger.info("Added %d GTFS knowledge pairs", len(knowledge_pairs))

    # Generate comparative pairs (category 8)
    comp_pairs = generate_comparative_pairs(summaries)
    logger.info("Generated %d comparative pairs", len(comp_pairs))

    # Combine all
    all_pairs = data_pairs + knowledge_pairs + comp_pairs
    all_pairs = deduplicate_pairs(all_pairs)

    # Shuffle
    rng.shuffle(all_pairs)

    # Write output
    write_jsonl(all_pairs, out_dir / "train.jsonl")
    report_path = write_report(all_pairs, out_dir)

    # Print summary
    print(f"\n{'=' * 60}")
    print("SYNTHETIC DATASET GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total pairs: {len(all_pairs):,}")

    category_counts: dict[str, int] = {}
    for p in all_pairs:
        cat = p.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    print("\nBy category:")
    for cat, count in sorted(category_counts.items()):
        print(f"  {cat}: {count}")
    print(f"\nOutput: {out_dir / 'train.jsonl'}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
