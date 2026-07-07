"""Validate the synthetic dataset and create train/test splits.

Checks format, content quality, distribution balance, and factual accuracy.
Produces a stratified train/test split and a validation report.
"""

import argparse
import json
import random
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from scripts.config import CLEANED_DIR, SYNTHETIC_DIR, get_logger

logger = get_logger(__name__)

REQUIRED_FIELDS = {"instruction", "response", "category", "template_id", "feed_id", "provider"}
MIN_RESPONSE_LENGTH = 20


def load_dataset(path: Path) -> list[dict]:
    """Load JSONL dataset."""
    pairs = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                pairs.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON on line %d: %s", i, e)
    return pairs


def validate_format(pairs: list[dict]) -> dict:
    """Check that all required fields are present in every record."""
    issues: list[str] = []
    for i, pair in enumerate(pairs):
        missing = REQUIRED_FIELDS - set(pair.keys())
        if missing:
            issues.append(f"Record {i}: missing fields {missing}")

    return {
        "check": "format",
        "passed": len(issues) == 0,
        "total_records": len(pairs),
        "issues_count": len(issues),
        "issues": issues[:20],  # Limit output
    }


def validate_content(pairs: list[dict]) -> dict:
    """Check content quality: no empty fields, minimum response length."""
    issues: list[str] = []
    inst_lengths: list[int] = []
    resp_lengths: list[int] = []

    for i, pair in enumerate(pairs):
        inst = pair.get("instruction", "")
        resp = pair.get("response", "")

        if not inst.strip():
            issues.append(f"Record {i}: empty instruction")
        if not resp.strip():
            issues.append(f"Record {i}: empty response")
        elif len(resp) < MIN_RESPONSE_LENGTH:
            issues.append(f"Record {i}: response too short ({len(resp)} chars)")

        inst_lengths.append(len(inst))
        resp_lengths.append(len(resp))

    return {
        "check": "content_quality",
        "passed": len(issues) == 0,
        "issues_count": len(issues),
        "issues": issues[:20],
        "instruction_length": {
            "min": min(inst_lengths) if inst_lengths else 0,
            "max": max(inst_lengths) if inst_lengths else 0,
            "avg": round(sum(inst_lengths) / len(inst_lengths), 1) if inst_lengths else 0,
        },
        "response_length": {
            "min": min(resp_lengths) if resp_lengths else 0,
            "max": max(resp_lengths) if resp_lengths else 0,
            "avg": round(sum(resp_lengths) / len(resp_lengths), 1) if resp_lengths else 0,
        },
    }


def check_duplicates(pairs: list[dict]) -> dict:
    """Check for duplicate instructions."""
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    for pair in pairs:
        inst = pair.get("instruction", "")
        if inst in seen:
            duplicates.append(inst[:100])
        else:
            seen[inst] = 1

    return {
        "check": "duplicates",
        "passed": len(duplicates) == 0,
        "duplicate_count": len(duplicates),
        "samples": duplicates[:10],
    }


def analyze_distribution(pairs: list[dict]) -> dict:
    """Analyze category, feed, and template distribution."""
    category_counts: dict[str, int] = defaultdict(int)
    feed_counts: dict[str, int] = defaultdict(int)
    template_counts: dict[str, int] = defaultdict(int)

    for pair in pairs:
        category_counts[pair.get("category", "unknown")] += 1
        fid = pair.get("feed_id", "")
        if fid:
            feed_counts[fid] += 1
        template_counts[pair.get("template_id", "unknown")] += 1

    # Category balance analysis
    total = len(pairs)
    category_pcts = {k: round(v / total * 100, 1) for k, v in category_counts.items()}

    return {
        "check": "distribution",
        "total_pairs": total,
        "categories": dict(sorted(category_counts.items())),
        "category_percentages": dict(sorted(category_pcts.items())),
        "feeds_covered": len(feed_counts),
        "feed_counts": dict(sorted(feed_counts.items())),
        "unique_templates": len(template_counts),
        "template_counts": dict(sorted(template_counts.items())),
    }


def spot_check_facts(pairs: list[dict], cleaned_dir: Path | None = None) -> dict:
    """Cross-reference numeric claims in responses against feed_summary.json."""
    cdir = cleaned_dir or CLEANED_DIR
    checks_performed = 0
    checks_passed = 0
    mismatches: list[str] = []

    # Load all feed summaries
    summaries: dict[str, dict] = {}
    for feed_dir in cdir.iterdir():
        if not feed_dir.is_dir() or not feed_dir.name.startswith("mdb-"):
            continue
        summary_path = feed_dir / "feed_summary.json"
        if summary_path.exists():
            with open(summary_path, encoding="utf-8") as f:
                data = json.load(f)
                summaries[data.get("feed_id", "")] = data

    # Check network_stats pairs (most verifiable)
    for pair in pairs:
        if pair.get("category") != "network_stats":
            continue

        feed_id = pair.get("feed_id", "")
        if feed_id not in summaries:
            continue

        summary = summaries[feed_id]
        response = pair.get("response", "")
        net_stats = summary.get("network_stats", {})

        # Check route count
        expected_routes = net_stats.get("total_routes", 0)
        route_match = re.search(r"(\d[\d,]*)\s+routes", response)
        if route_match and expected_routes > 0:
            checks_performed += 1
            found = int(route_match.group(1).replace(",", ""))
            if found == expected_routes:
                checks_passed += 1
            else:
                mismatches.append(
                    f"Feed {feed_id}: route count {found} != expected {expected_routes}"
                )

        # Check stop count
        expected_stops = net_stats.get("total_stops", 0)
        stop_match = re.search(r"(\d[\d,]*)\s+stops", response)
        if stop_match and expected_stops > 0:
            checks_performed += 1
            found = int(stop_match.group(1).replace(",", ""))
            if found == expected_stops:
                checks_passed += 1
            else:
                mismatches.append(
                    f"Feed {feed_id}: stop count {found} != expected {expected_stops}"
                )

    # Also check agency_route_count pairs
    for pair in pairs:
        if pair.get("template_id") != "agency_route_count_v1":
            continue

        feed_id = pair.get("feed_id", "")
        if feed_id not in summaries:
            continue

        summary = summaries[feed_id]
        response = pair.get("response", "")
        expected = summary.get("route_summary", {}).get("total_routes", 0)

        route_match = re.search(r"operates\s+(\d[\d,]*)\s+routes", response)
        if route_match and expected > 0:
            checks_performed += 1
            found = int(route_match.group(1).replace(",", ""))
            if found == expected:
                checks_passed += 1
            else:
                mismatches.append(
                    f"Feed {feed_id}: agency route count {found} != expected {expected}"
                )

    return {
        "check": "factual_accuracy",
        "passed": len(mismatches) == 0,
        "checks_performed": checks_performed,
        "checks_passed": checks_passed,
        "accuracy": round(checks_passed / checks_performed * 100, 1) if checks_performed > 0 else 0,
        "mismatches": mismatches[:20],
    }


def split_dataset(
    pairs: list[dict],
    train_ratio: float = 0.9,
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """Stratified train/test split by category."""
    rng = random.Random(seed)

    # Group by category
    by_category: dict[str, list[dict]] = defaultdict(list)
    for pair in pairs:
        by_category[pair.get("category", "unknown")].append(pair)

    train: list[dict] = []
    test: list[dict] = []

    for category, cat_pairs in by_category.items():
        rng.shuffle(cat_pairs)
        split_idx = int(len(cat_pairs) * train_ratio)
        # Ensure at least 1 in test if category has >= 2 items
        if split_idx == len(cat_pairs) and len(cat_pairs) >= 2:
            split_idx -= 1
        train.extend(cat_pairs[:split_idx])
        test.extend(cat_pairs[split_idx:])

    rng.shuffle(train)
    rng.shuffle(test)

    return train, test


def write_jsonl(pairs: list[dict], path: Path) -> None:
    """Write pairs to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")


def main() -> None:
    """Run all validation checks, split dataset, write report."""
    parser = argparse.ArgumentParser(description="Validate synthetic dataset")
    parser.add_argument("--input", type=Path, default=None, help="Input JSONL path")
    parser.add_argument("--split-ratio", type=float, default=0.9, help="Train ratio (default 0.9)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    input_path = args.input or (SYNTHETIC_DIR / "train.jsonl")
    if not input_path.exists():
        logger.error("Dataset not found at %s", input_path)
        raise SystemExit(1)

    # Load dataset
    logger.info("Loading dataset from %s", input_path)
    pairs = load_dataset(input_path)
    logger.info("Loaded %d pairs", len(pairs))

    # Run validation checks
    checks = []

    logger.info("Checking format...")
    checks.append(validate_format(pairs))

    logger.info("Checking content quality...")
    checks.append(validate_content(pairs))

    logger.info("Checking duplicates...")
    checks.append(check_duplicates(pairs))

    logger.info("Analyzing distribution...")
    dist = analyze_distribution(pairs)
    checks.append(dist)

    logger.info("Spot-checking factual accuracy...")
    checks.append(spot_check_facts(pairs))

    # Overall pass/fail
    all_passed = all(c.get("passed", True) for c in checks if "passed" in c)

    # Split dataset
    logger.info("Splitting dataset (%.0f%% train)...", args.split_ratio * 100)
    train, test = split_dataset(pairs, args.split_ratio, args.seed)

    # Write split files
    train_path = SYNTHETIC_DIR / "train.jsonl"
    test_path = SYNTHETIC_DIR / "test.jsonl"
    write_jsonl(train, train_path)
    write_jsonl(test, test_path)
    logger.info("Train: %d pairs -> %s", len(train), train_path)
    logger.info("Test:  %d pairs -> %s", len(test), test_path)

    # Write validation report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_path),
        "total_pairs": len(pairs),
        "all_checks_passed": all_passed,
        "train_size": len(train),
        "test_size": len(test),
        "split_ratio": args.split_ratio,
        "checks": checks,
    }

    report_path = SYNTHETIC_DIR / "validation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'=' * 60}")
    print("DATASET VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"Total pairs:    {len(pairs):,}")
    print(f"All checks:     {'PASSED' if all_passed else 'FAILED'}")
    print()

    for check in checks:
        name = check.get("check", "unknown")
        passed = check.get("passed", True)
        status = "PASS" if passed else "FAIL"
        detail = ""
        if name == "content_quality":
            il = check["instruction_length"]
            rl = check["response_length"]
            detail = f" (inst: {il['min']}-{il['max']} avg {il['avg']}, resp: {rl['min']}-{rl['max']} avg {rl['avg']})"
        elif name == "distribution":
            detail = f" ({check['feeds_covered']} feeds, {check['unique_templates']} templates)"
        elif name == "factual_accuracy":
            detail = f" ({check['checks_passed']}/{check['checks_performed']} = {check['accuracy']}%)"
        elif name == "duplicates":
            detail = f" ({check['duplicate_count']} found)"
        print(f"  {name:20s} [{status}]{detail}")

    print(f"\nSplit: {len(train):,} train / {len(test):,} test")
    print(f"\nCategory distribution (test set):")
    test_cats: dict[str, int] = defaultdict(int)
    for p in test:
        test_cats[p.get("category", "")] += 1
    for cat, count in sorted(test_cats.items()):
        print(f"  {cat}: {count}")

    print(f"\nReport: {report_path}")


if __name__ == "__main__":
    main()
