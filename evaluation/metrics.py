"""Scoring metrics for UmarTransit benchmark evaluation.

Three scoring dimensions:
1. ROUGE-L       — Content overlap between generated and expected answers
2. Keyword Match — Fraction of key numbers/facts from expected that appear in generated
3. Criteria Match — Whether scoring_criteria keywords are present in the generated answer

Usage:
    from metrics import score_response, score_benchmark, print_report

    result = score_response(
        generated="GTFS stands for General Transit Feed Specification...",
        expected="GTFS stands for General Transit Feed Specification...",
        scoring_criteria="Must mention: General Transit Feed Specification, open standard",
    )

    report = score_benchmark(results)
    print_report(report)
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field

import nltk
from rouge_score import rouge_scorer

# Ensure nltk tokenizer data is available
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)

_scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Individual scoring functions
# ═══════════════════════════════════════════════════════════════════════════════

def rouge_l(expected: str, generated: str) -> float:
    """Compute ROUGE-L F1 between expected and generated text."""
    if not generated.strip():
        return 0.0
    score = _scorer.score(expected, generated)
    return score["rougeL"].fmeasure


def keyword_match(expected: str, generated: str) -> float:
    """Check what fraction of key numbers from expected appear in generated.

    Extracts all numbers (with commas stripped) and checks overlap.
    Returns 1.0 if no numbers to check.
    """
    expected_nums = set(re.findall(r"\b\d[\d,]*\.?\d*\b", expected.replace(",", "")))
    if not expected_nums:
        return 1.0
    generated_nums = set(re.findall(r"\b\d[\d,]*\.?\d*\b", generated.replace(",", "")))
    matched = expected_nums & generated_nums
    return len(matched) / len(expected_nums)


def criteria_match(scoring_criteria: str, generated: str) -> float:
    """Score how well the generated answer matches the scoring criteria.

    Parses criteria for required keywords/phrases and checks presence.
    Handles patterns like:
      - "Must mention: term1, term2, term3"
      - "Must mention X and Y"
      - "Must state X"
      - "Must list at least types 0, 1, 2"
      - "Must explain X"
      - "Must identify X"
    """
    if not scoring_criteria or not generated:
        return 0.0

    generated_lower = generated.lower()

    # Extract key phrases from criteria text
    # Remove common prefixes
    text = scoring_criteria
    text = re.sub(r"^Must\s+(mention|state|explain|identify|list|note|confirm|distinguish|define|contrast|calculate)\s*:?\s*", "", text, flags=re.IGNORECASE)

    # Split on common delimiters
    # Handle "X and Y", "X, Y, Z", "X or Y"
    # Also handle "at least N of:" patterns
    at_least_match = re.search(r"at least (\d+) of:?\s*", text, re.IGNORECASE)
    min_required = None
    if at_least_match:
        min_required = int(at_least_match.group(1))
        text = text[at_least_match.end():]

    # Split into check terms
    terms = re.split(r",\s*|\s+and\s+|\s+or\s+", text)
    terms = [t.strip().strip("()") for t in terms if t.strip() and len(t.strip()) > 1]

    if not terms:
        return 0.0

    hits = sum(1 for term in terms if term.lower() in generated_lower)

    if min_required is not None:
        return 1.0 if hits >= min_required else hits / min_required

    return hits / len(terms)


# ═══════════════════════════════════════════════════════════════════════════════
# Combined scoring
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScoreResult:
    """Scores for a single benchmark question."""
    rouge_l: float
    keyword_match: float
    criteria_match: float
    combined: float  # weighted average


def score_response(
    generated: str,
    expected: str,
    scoring_criteria: str,
    weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
) -> ScoreResult:
    """Score a single generated response against expected answer and criteria.

    Args:
        generated: The model's response
        expected: The expected/reference answer
        scoring_criteria: What must be present in the answer
        weights: (rouge_l, keyword, criteria) weights for combined score
    """
    r = rouge_l(expected, generated)
    k = keyword_match(expected, generated)
    c = criteria_match(scoring_criteria, generated)
    combined = weights[0] * r + weights[1] * k + weights[2] * c
    return ScoreResult(rouge_l=r, keyword_match=k, criteria_match=c, combined=combined)


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark-level aggregation
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CategoryReport:
    """Aggregated scores for one category."""
    count: int = 0
    rouge_l_avg: float = 0.0
    keyword_match_avg: float = 0.0
    criteria_match_avg: float = 0.0
    combined_avg: float = 0.0
    by_difficulty: dict = field(default_factory=dict)


@dataclass
class BenchmarkReport:
    """Full benchmark evaluation report."""
    model_id: str
    total_questions: int
    overall_rouge_l: float
    overall_keyword_match: float
    overall_criteria_match: float
    overall_combined: float
    categories: dict[str, CategoryReport]
    difficulty_breakdown: dict[str, dict]


def score_benchmark(
    results: list[dict],
    model_id: str = "unknown",
) -> BenchmarkReport:
    """Score all benchmark results and produce an aggregated report.

    Args:
        results: List of dicts with keys:
            - generated: model output
            - expected_answer: reference answer
            - scoring_criteria: criteria string
            - category: question category
            - difficulty: easy/medium/hard
        model_id: Name of the model being evaluated
    """
    all_scores: list[ScoreResult] = []
    cat_scores: dict[str, list[tuple[ScoreResult, str]]] = defaultdict(list)

    for r in results:
        s = score_response(
            generated=r.get("generated", ""),
            expected=r.get("expected_answer", ""),
            scoring_criteria=r.get("scoring_criteria", ""),
        )
        all_scores.append(s)
        cat_scores[r.get("category", "unknown")].append((s, r.get("difficulty", "medium")))

    n = len(all_scores) or 1

    # Overall averages
    overall_r = sum(s.rouge_l for s in all_scores) / n
    overall_k = sum(s.keyword_match for s in all_scores) / n
    overall_c = sum(s.criteria_match for s in all_scores) / n
    overall_combined = sum(s.combined for s in all_scores) / n

    # Per-category
    categories: dict[str, CategoryReport] = {}
    for cat, score_list in sorted(cat_scores.items()):
        cn = len(score_list) or 1
        by_diff: dict[str, dict] = defaultdict(lambda: {"count": 0, "combined_sum": 0.0})
        for s, diff in score_list:
            by_diff[diff]["count"] += 1
            by_diff[diff]["combined_sum"] += s.combined

        diff_report = {}
        for diff, d in by_diff.items():
            diff_report[diff] = round(d["combined_sum"] / d["count"], 4) if d["count"] else 0.0

        categories[cat] = CategoryReport(
            count=cn,
            rouge_l_avg=round(sum(s.rouge_l for s, _ in score_list) / cn, 4),
            keyword_match_avg=round(sum(s.keyword_match for s, _ in score_list) / cn, 4),
            criteria_match_avg=round(sum(s.criteria_match for s, _ in score_list) / cn, 4),
            combined_avg=round(sum(s.combined for s, _ in score_list) / cn, 4),
            by_difficulty=diff_report,
        )

    # Difficulty breakdown
    diff_scores: dict[str, list[float]] = defaultdict(list)
    for r, s in zip(results, all_scores):
        diff_scores[r.get("difficulty", "medium")].append(s.combined)
    difficulty_breakdown = {
        d: {"count": len(scores), "combined_avg": round(sum(scores) / len(scores), 4)}
        for d, scores in sorted(diff_scores.items())
    }

    return BenchmarkReport(
        model_id=model_id,
        total_questions=len(all_scores),
        overall_rouge_l=round(overall_r, 4),
        overall_keyword_match=round(overall_k, 4),
        overall_criteria_match=round(overall_c, 4),
        overall_combined=round(overall_combined, 4),
        categories=categories,
        difficulty_breakdown=difficulty_breakdown,
    )


def print_report(report: BenchmarkReport) -> None:
    """Print a formatted evaluation report to stdout."""
    print("=" * 72)
    print(f"  BENCHMARK EVALUATION REPORT: {report.model_id}")
    print("=" * 72)
    print(f"  Total questions:    {report.total_questions}")
    print(f"  ROUGE-L (avg):      {report.overall_rouge_l:.4f}")
    print(f"  Keyword Match:      {report.overall_keyword_match:.4f}")
    print(f"  Criteria Match:     {report.overall_criteria_match:.4f}")
    print(f"  Combined Score:     {report.overall_combined:.4f}")

    print("\n" + "-" * 72)
    print(f"  {'Category':<25} {'Count':>6} {'ROUGE-L':>9} {'Keyword':>9} {'Criteria':>9} {'Combined':>9}")
    print("-" * 72)
    for cat, cr in sorted(report.categories.items()):
        print(f"  {cat:<25} {cr.count:>6} {cr.rouge_l_avg:>9.4f} {cr.keyword_match_avg:>9.4f} {cr.criteria_match_avg:>9.4f} {cr.combined_avg:>9.4f}")
    print("-" * 72)
    print(f"  {'OVERALL':<25} {report.total_questions:>6} {report.overall_rouge_l:>9.4f} {report.overall_keyword_match:>9.4f} {report.overall_criteria_match:>9.4f} {report.overall_combined:>9.4f}")

    print("\n" + "-" * 72)
    print("  Difficulty Breakdown:")
    for diff, info in sorted(report.difficulty_breakdown.items()):
        print(f"    {diff:<10} {info['count']:>4} questions   combined avg: {info['combined_avg']:.4f}")
    print("=" * 72)


def report_to_dict(report: BenchmarkReport) -> dict:
    """Convert a BenchmarkReport to a JSON-serializable dict."""
    return {
        "model_id": report.model_id,
        "total_questions": report.total_questions,
        "overall": {
            "rouge_l": report.overall_rouge_l,
            "keyword_match": report.overall_keyword_match,
            "criteria_match": report.overall_criteria_match,
            "combined": report.overall_combined,
        },
        "categories": {
            cat: {
                "count": cr.count,
                "rouge_l_avg": cr.rouge_l_avg,
                "keyword_match_avg": cr.keyword_match_avg,
                "criteria_match_avg": cr.criteria_match_avg,
                "combined_avg": cr.combined_avg,
                "by_difficulty": cr.by_difficulty,
            }
            for cat, cr in sorted(report.categories.items())
        },
        "difficulty_breakdown": report.difficulty_breakdown,
    }
