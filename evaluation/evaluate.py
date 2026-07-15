"""Benchmark evaluation runner for UmarTransit.

Runs both the base model (Qwen2.5-1.5B-Instruct) and UmarTransit-1B
against benchmark.json, scores responses, and saves a comparison report.

Works on both local CPU and Google Colab GPU.

Usage (local, quick test with 5 questions):
    python -m evaluation.evaluate --limit 5

Usage (full benchmark on Colab):
    python -m evaluation.evaluate

Usage (single model only):
    python -m evaluation.evaluate --model umartransit
    python -m evaluation.evaluate --model base
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm

# Handle both local and Colab imports
try:
    from evaluation.metrics import score_response, score_benchmark, print_report, report_to_dict
except ImportError:
    from metrics import score_response, score_benchmark, print_report, report_to_dict

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
UMARTRANSIT_MODEL_ID = "umarfarookm/UmarTransit-1B"

MAX_NEW_TOKENS = 256
TEMPERATURE = 0.1
TOP_P = 0.9

SYSTEM_PROMPT = (
    "You are UmarTransit-1B, a specialized AI assistant for public transit systems "
    "and GTFS (General Transit Feed Specification) data. You provide accurate, "
    "detailed answers about transit routes, stops, schedules, transfers, and GTFS concepts."
)

# For base model, use a generic system prompt
BASE_SYSTEM_PROMPT = (
    "You are a helpful AI assistant that answers questions about public transit systems "
    "and GTFS (General Transit Feed Specification) data."
)

EVAL_DIR = Path(__file__).resolve().parent
BENCHMARK_PATH = EVAL_DIR / "benchmark.json"
RESULTS_DIR = EVAL_DIR / "results"


# ── Model loading ─────────────────────────────────────────────────────────────

def detect_device() -> tuple[str, torch.dtype]:
    """Detect the best available device and dtype."""
    if torch.cuda.is_available():
        return "auto", torch.bfloat16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", torch.float32
    else:
        return "cpu", torch.float32


def load_model(model_id: str) -> tuple:
    """Load a model and tokenizer."""
    device_map, dtype = detect_device()
    print(f"Loading {model_id} (device={device_map}, dtype={dtype})...")
    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map=device_map,
    )
    model.eval()

    elapsed = time.time() - start
    print(f"  Loaded in {elapsed:.1f}s")

    if torch.cuda.is_available():
        mem = torch.cuda.memory_allocated() / 1024**3
        print(f"  GPU memory: {mem:.1f} GB")

    return model, tokenizer


def generate_response(model, tokenizer, question: str, system_prompt: str) -> str:
    """Generate a response for a single question."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
    )
    inputs = tokenizer(text, return_tensors="pt")

    # Move to model device
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}
    input_len = inputs["input_ids"].shape[-1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            do_sample=True,
        )

    response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
    return response.strip()


# ── Evaluation ────────────────────────────────────────────────────────────────

def run_evaluation(
    model,
    tokenizer,
    questions: list[dict],
    model_id: str,
    system_prompt: str,
) -> list[dict]:
    """Run all benchmark questions through a model and score responses."""
    results = []

    for q in tqdm(questions, desc=f"Evaluating {model_id.split('/')[-1]}"):
        start = time.time()
        generated = generate_response(model, tokenizer, q["question"], system_prompt)
        elapsed = time.time() - start

        score = score_response(
            generated=generated,
            expected=q["expected_answer"],
            scoring_criteria=q["scoring_criteria"],
        )

        results.append({
            "id": q["id"],
            "question": q["question"],
            "expected_answer": q["expected_answer"],
            "generated": generated,
            "scoring_criteria": q["scoring_criteria"],
            "category": q["category"],
            "difficulty": q["difficulty"],
            "rouge_l": round(score.rouge_l, 4),
            "keyword_match": round(score.keyword_match, 4),
            "criteria_match": round(score.criteria_match, 4),
            "combined": round(score.combined, 4),
            "time_seconds": round(elapsed, 2),
        })

    return results


def save_results(
    results: list[dict],
    report: dict,
    model_name: str,
) -> Path:
    """Save evaluation results to JSON."""
    RESULTS_DIR.mkdir(exist_ok=True)
    output = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "report": report,
        "results": results,
    }
    path = RESULTS_DIR / f"{model_name}_results.json"
    with open(path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {path}")
    return path


def print_comparison(base_report: dict, umar_report: dict) -> None:
    """Print a side-by-side comparison of two models."""
    print("\n" + "=" * 80)
    print("  SIDE-BY-SIDE COMPARISON: Base Model vs UmarTransit-1B")
    print("=" * 80)

    print(f"\n  {'Metric':<25} {'Base Model':>15} {'UmarTransit':>15} {'Delta':>10}")
    print("  " + "-" * 65)

    for metric in ["rouge_l", "keyword_match", "criteria_match", "combined"]:
        base_val = base_report["overall"][metric]
        umar_val = umar_report["overall"][metric]
        delta = umar_val - base_val
        sign = "+" if delta > 0 else ""
        print(f"  {metric:<25} {base_val:>15.4f} {umar_val:>15.4f} {sign}{delta:>9.4f}")

    print(f"\n  {'Category':<25} {'Base Combined':>15} {'Umar Combined':>15} {'Delta':>10}")
    print("  " + "-" * 65)

    all_cats = sorted(set(list(base_report["categories"].keys()) + list(umar_report["categories"].keys())))
    for cat in all_cats:
        base_val = base_report["categories"].get(cat, {}).get("combined_avg", 0)
        umar_val = umar_report["categories"].get(cat, {}).get("combined_avg", 0)
        delta = umar_val - base_val
        sign = "+" if delta > 0 else ""
        print(f"  {cat:<25} {base_val:>15.4f} {umar_val:>15.4f} {sign}{delta:>9.4f}")

    print("=" * 80)

    # Verdict
    overall_delta = umar_report["overall"]["combined"] - base_report["overall"]["combined"]
    if overall_delta > 0.05:
        verdict = "UmarTransit-1B significantly outperforms the base model."
    elif overall_delta > 0:
        verdict = "UmarTransit-1B slightly outperforms the base model."
    elif overall_delta > -0.05:
        verdict = "Performance is roughly equivalent."
    else:
        verdict = "The base model outperforms UmarTransit-1B."
    print(f"\n  Verdict: {verdict} (delta={overall_delta:+.4f})")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="UmarTransit Benchmark Evaluation")
    parser.add_argument(
        "--model", choices=["both", "base", "umartransit"],
        default="both", help="Which model(s) to evaluate (default: both)",
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit to N questions for quick testing (0 = all)",
    )
    parser.add_argument(
        "--benchmark", type=str, default=str(BENCHMARK_PATH),
        help="Path to benchmark.json",
    )
    args = parser.parse_args()

    # Load benchmark
    benchmark_path = Path(args.benchmark)
    with open(benchmark_path) as f:
        benchmark = json.load(f)

    questions = benchmark["questions"]
    if args.limit > 0:
        questions = questions[:args.limit]

    print(f"Benchmark: {benchmark['metadata']['name']}")
    print(f"Questions: {len(questions)} (of {benchmark['metadata']['total_questions']} total)")
    print(f"Device:    {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print()

    base_report_dict = None
    umar_report_dict = None

    # Evaluate base model
    if args.model in ("both", "base"):
        model, tokenizer = load_model(BASE_MODEL_ID)
        base_results = run_evaluation(model, tokenizer, questions, BASE_MODEL_ID, BASE_SYSTEM_PROMPT)
        base_report = score_benchmark(base_results, model_id=BASE_MODEL_ID)
        print_report(base_report)
        base_report_dict = report_to_dict(base_report)
        save_results(base_results, base_report_dict, "base_model")

        # Free memory before loading next model
        del model, tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # Evaluate UmarTransit
    if args.model in ("both", "umartransit"):
        model, tokenizer = load_model(UMARTRANSIT_MODEL_ID)
        umar_results = run_evaluation(model, tokenizer, questions, UMARTRANSIT_MODEL_ID, SYSTEM_PROMPT)
        umar_report = score_benchmark(umar_results, model_id=UMARTRANSIT_MODEL_ID)
        print_report(umar_report)
        umar_report_dict = report_to_dict(umar_report)
        save_results(umar_results, umar_report_dict, "umartransit")

        del model, tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    # Comparison
    if base_report_dict and umar_report_dict:
        print_comparison(base_report_dict, umar_report_dict)

        # Save comparison
        RESULTS_DIR.mkdir(exist_ok=True)
        comparison = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "questions_evaluated": len(questions),
            "base_model": base_report_dict,
            "umartransit": umar_report_dict,
        }
        comp_path = RESULTS_DIR / "comparison.json"
        with open(comp_path, "w") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print(f"Comparison saved to: {comp_path}")


if __name__ == "__main__":
    main()
