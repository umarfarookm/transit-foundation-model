# Evaluation Results: UmarTransit-1B vs Base Model

**Benchmark Version:** 1.0  
**Evaluated:** 2026-07-15  
**Questions:** 193 across 6 categories  
**Models compared:**
- **Base:** Qwen/Qwen2.5-1.5B-Instruct (no fine-tuning)
- **Fine-tuned:** umarfarookm/UmarTransit-1B (QLoRA on 2,971 transit Q&A pairs)

**Hardware:** Google Colab T4 GPU

---

## Overall Results

| Metric | Base Model | UmarTransit-1B | Delta |
|--------|-----------|----------------|-------|
| ROUGE-L | 0.1290 | 0.3751 | **+0.2461** |
| Keyword Match | 0.3678 | 0.4034 | **+0.0356** |
| Criteria Match | 0.0203 | 0.0721 | **+0.0518** |
| **Combined Score** | **0.1680** | **0.2927** | **+0.1247** |

**Verdict: UmarTransit-1B significantly outperforms the base model** with a +74% relative improvement in combined score.

---

## Per-Category Breakdown

| Category | Base Combined | UmarTransit Combined | Delta | Winner |
|----------|--------------|---------------------|-------|--------|
| GTFS Terminology | 0.3420 | 0.3512 | +0.0092 | UmarTransit |
| GTFS Validation | 0.2667 | 0.3137 | +0.0470 | UmarTransit |
| Route Analysis | 0.0843 | 0.2901 | **+0.2058** | UmarTransit |
| Journey Planning | 0.2967 | 0.2426 | -0.0541 | Base |
| Schedule Reasoning | 0.1205 | 0.2525 | **+0.1320** | UmarTransit |
| Transit Operations | 0.1927 | 0.3065 | **+0.1138** | UmarTransit |

**UmarTransit wins 5 of 6 categories.** The largest gains are in data-driven categories (Route Analysis, Schedule Reasoning) where the fine-tuning data directly applies.

---

## Difficulty Breakdown

| Difficulty | Base Combined | UmarTransit Combined | Delta |
|------------|--------------|---------------------|-------|
| Easy (78 Qs) | 0.1467 | 0.3737 | **+0.2270** |
| Medium (102 Qs) | 0.1719 | 0.2296 | +0.0577 |
| Hard (13 Qs) | 0.2654 | 0.3011 | +0.0357 |

UmarTransit shows the strongest improvement on easy questions, where domain-specific knowledge matters most.

---

## Key Findings

### Where UmarTransit excels

**Route Analysis (+0.2058):** The fine-tuned model knows actual transit agency data — route counts, transit modes, and network sizes. The base model guesses or hallucinates these numbers.

Example — *"How many transit routes does OVapi Netherlands operate?"*
- Base: *"approximately 1,000 bus routes"* (wrong)
- UmarTransit: *"3,114 routes of which 259 are Tram/Streetcar/Light rail"* (correct)

**Schedule Reasoning (+0.1320):** UmarTransit correctly recalls operating hours, trip counts, and service patterns from real GTFS feeds.

**Transit Operations (+0.1138):** Better at describing network sizes and operational concepts when grounded in real data.

### Where Base model holds its own

**Journey Planning (-0.0541):** The base model performs slightly better on abstract reasoning about transfer logic and service scheduling — areas where general language understanding matters more than domain-specific fine-tuning.

**GTFS Terminology (+0.0092):** Near-tie. Both models have reasonable knowledge of GTFS spec concepts. The base model benefits from pre-training on web content that includes GTFS documentation.

### Weakness: Criteria Match is low for both

Both models score low on criteria match (Base: 0.02, UmarTransit: 0.07). This means neither model consistently uses the exact terminology expected by the scoring criteria. This is an area for improvement in future training — the model should learn to include specific GTFS field names and values in its responses.

---

## Per-Category ROUGE-L Detail

| Category | Base ROUGE-L | UmarTransit ROUGE-L | Delta |
|----------|-------------|---------------------|-------|
| GTFS Terminology | 0.1270 | 0.2296 | +0.1026 |
| GTFS Validation | 0.1446 | 0.2094 | +0.0648 |
| Route Analysis | 0.1138 | 0.4174 | **+0.3036** |
| Journey Planning | 0.1418 | 0.2378 | +0.0960 |
| Schedule Reasoning | 0.1486 | 0.4609 | **+0.3123** |
| Transit Operations | 0.1300 | 0.4328 | **+0.3028** |

ROUGE-L improvements are dramatic across all categories, with 3x gains in Route Analysis, Schedule Reasoning, and Transit Operations.

---

## Conclusion

Fine-tuning on 2,971 transit-specific Q&A pairs produces measurable improvements across nearly all evaluation categories. The model learns factual transit data effectively and generates responses that are structurally closer to expected answers.

**Areas for improvement in v1.0 training:**
1. **Journey planning reasoning** — Add more multi-step transfer and scheduling logic questions
2. **GTFS terminology depth** — Add more questions about advanced fields (pathways, fare attributes, flex service)
3. **Criteria precision** — Train the model to include specific field names and values in responses
4. **Expand training data** — Current 2,971 pairs are effective but more data would improve generalization

---

*Generated from benchmark evaluation results. Full prediction data available in `evaluation/results/`.*
