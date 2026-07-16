# Evaluation Results: Base Model vs v0.1 vs v1.0

**Benchmark Version:** 1.0
**Evaluated:** 2026-07-16
**Questions:** 193 across 6 categories
**Models compared:**
- **Base:** Qwen/Qwen2.5-1.5B-Instruct (no fine-tuning)
- **v0.1:** UmarTransit-1B trained on 2,971 pairs (8 categories)
- **v1.0:** UmarTransit-1B trained on 3,501 pairs (11 categories — added journey planning, GTFS validation, transit operations)

**Hardware:** Google Colab T4 GPU

---

## Overall Results

| Metric | Base | v0.1 | v1.0 | v0.1 → v1.0 |
|--------|------|------|------|-------------|
| ROUGE-L | 0.1290 | 0.3751 | 0.4091 | **+0.0340** |
| Keyword Match | 0.3678 | 0.4034 | 0.3981 | -0.0053 |
| Criteria Match | 0.0203 | 0.0721 | 0.0984 | **+0.0263** |
| **Combined Score** | **0.1680** | **0.2927** | **0.3126** | **+0.0199** |

**v1.0 improves over v0.1 by +6.8%** in combined score. Overall improvement over the base model is **+86%**.

---

## Per-Category Comparison

| Category | Base | v0.1 | v1.0 | v0.1 → v1.0 |
|----------|------|------|------|-------------|
| GTFS Terminology | 0.3420 | 0.3512 | 0.3608 | +0.0096 |
| GTFS Validation | 0.2667 | 0.3137 | 0.3227 | +0.0090 |
| Route Analysis | 0.0843 | 0.2901 | 0.3284 | **+0.0383** |
| Journey Planning | 0.2967 | 0.2426 | 0.3107 | **+0.0681** |
| Schedule Reasoning | 0.1205 | 0.2525 | 0.2244 | -0.0281 |
| Transit Operations | 0.1927 | 0.3065 | 0.3422 | **+0.0357** |

**v1.0 wins all 6 categories against the base model.** Compared to v0.1, v1.0 improves in 5 of 6 categories.

---

## Key Improvements in v1.0

### Journey Planning: fixed (+0.0681 vs v0.1)

The biggest v0.1 weakness was journey planning — it scored **worse than the base model** (0.2426 vs 0.2967). After adding 100 journey planning training pairs, v1.0 scores **0.3107**, now beating the base model by +0.014. This was the most impactful change.

### Route Analysis: stronger (+0.0383 vs v0.1)

Already the strongest v0.1 category, route analysis improved further to 0.3284 — nearly **4x the base model** (0.0843).

### Transit Operations: stronger (+0.0357 vs v0.1)

With 20 new transit operations pairs, the model improved from 0.3065 to 0.3422 — the highest score across all categories.

### Criteria Match: improved (+0.0263 vs v0.1)

The expanded GTFS knowledge and validation pairs helped the model learn to include specific field names and terminology in responses. Criteria match rose from 0.0721 to 0.0984 — still room to improve, but a meaningful step.

---

## Difficulty Breakdown

| Difficulty | Base | v0.1 | v1.0 | v0.1 → v1.0 |
|------------|------|------|------|-------------|
| Easy (78 Qs) | 0.1467 | 0.3737 | 0.3846 | +0.0109 |
| Medium (102 Qs) | 0.1719 | 0.2296 | 0.2566 | **+0.0270** |
| Hard (13 Qs) | 0.2654 | 0.3011 | 0.3201 | +0.0190 |

v1.0 improves across all difficulty levels, with the largest gain on medium-difficulty questions.

---

## What Changed Between v0.1 and v1.0

| | v0.1 | v1.0 |
|--|------|------|
| Training pairs | 2,971 | 3,154 (+183) |
| Test pairs | 335 | 347 (+12) |
| Total categories | 8 | 11 (+3 new) |
| New: journey_planning | 0 pairs | 100 pairs |
| New: gtfs_validation | 0 pairs | 20 pairs |
| New: transit_operations | 0 pairs | 20 pairs |
| Expanded: gtfs_knowledge | 22 pairs | 53 pairs |
| Expanded: network_stats | 30 pairs | 45 pairs |
| Expanded: comparative | 14 pairs | 23 pairs |

---

## Remaining Weaknesses

1. **Schedule Reasoning** dropped slightly (-0.0281) — the new training data didn't include additional schedule pairs, and the model may have shifted attention toward the new categories
2. **Keyword Match** is flat (-0.005) — the model generates relevant text but doesn't always include exact numbers from the expected answers
3. **Criteria Match** (0.098) is still the weakest metric — the model needs more training on using precise GTFS field names in responses

---

## Conclusion

Adding 195 targeted training pairs to address benchmark weaknesses produced measurable improvement:
- **Journey planning**: fixed from below-baseline to above-baseline
- **Overall combined score**: +6.8% over v0.1, +86% over base
- **All 6 categories** now beat the base model (vs 5/6 in v0.1)

The expanded dataset (3,501 pairs) and v1.0 model are published on HuggingFace:
- Model: [umarfarookm/UmarTransit-1B](https://huggingface.co/umarfarookm/UmarTransit-1B)
- Dataset: [umarfarookm/UmarTransit-Instruct-3k](https://huggingface.co/datasets/umarfarookm/UmarTransit-Instruct-3k)

*To reproduce, run `evaluation/benchmark_v1_colab.ipynb` on Google Colab with T4 GPU.*
