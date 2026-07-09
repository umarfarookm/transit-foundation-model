# UmarTransit-1B: Complete Step-by-Step Build Guide

A comprehensive guide to building a domain-specific foundation model for public transit, from zero to deployment. This document covers every decision, concept, and command across all 12 phases.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Phase 1: Project Setup](#2-phase-1-project-setup)
3. [Phase 2: GTFS Dataset Collection](#3-phase-2-gtfs-dataset-collection)
4. [Phase 3: Data Cleaning](#4-phase-3-data-cleaning)
5. [Phase 4: Synthetic Dataset Generation](#5-phase-4-synthetic-dataset-generation)
6. [Phase 5: Dataset Validation](#6-phase-5-dataset-validation)
7. [Phase 6: Base Model Selection](#7-phase-6-base-model-selection)
8. [Phase 7: QLoRA Training](#8-phase-7-qlora-training)
9. [Phase 8: Evaluation](#9-phase-8-evaluation)
10. [Phase 9: Model Optimization](#10-phase-9-model-optimization)
11. [Phase 10: HuggingFace Publishing](#11-phase-10-huggingface-publishing)
12. [Phase 11: Local Inference](#12-phase-11-local-inference)
13. [Phase 12: Web Application](#13-phase-12-web-application)
14. [Future Improvements](#14-future-improvements)

---

## 1. Project Overview

### What We're Building

UmarTransit-1B is a **domain-specific language model** — a large language model (LLM) that has been fine-tuned to specialize in public transit systems and GTFS data. Unlike general-purpose models like ChatGPT, UmarTransit-1B is trained specifically on transit data and can answer questions about routes, stops, schedules, and the GTFS specification.

### What is a Foundation Model?

A foundation model is a large AI model trained on broad data that can be adapted (fine-tuned) for specific tasks. Think of it like a university graduate (general knowledge) who then does a specialized residency (domain training). We take an existing model (Qwen2.5-1.5B) and teach it transit-specific knowledge.

### What is GTFS?

GTFS (General Transit Feed Specification) is an open standard created by Google and TriMet (Portland, OR) in 2005. Transit agencies worldwide publish their schedule data in GTFS format — a ZIP file containing CSV files:

| File | Purpose | Example Data |
|------|---------|-------------|
| `agency.txt` | Transit agency info | "Chicago Transit Authority", timezone |
| `routes.txt` | Route definitions | Route 22, Bus, "Clark Street" |
| `trips.txt` | Individual trips | Trip 1234, Route 22, Northbound |
| `stops.txt` | Stop locations | "Clark & Belmont", lat/lon |
| `stop_times.txt` | Arrival/departure times | Trip 1234 arrives Stop 567 at 08:15 |
| `calendar.txt` | Service schedules | Weekdays, Jan-Jun 2026 |

These files are linked by IDs (like database foreign keys) — `route_id` connects routes to trips, `trip_id` connects trips to stop_times, etc.

### What is Fine-Tuning?

Fine-tuning takes a pre-trained model and trains it further on domain-specific data. The analogy in backend engineering:

- **Pre-trained model** = A Spring Boot starter template with common configurations
- **Fine-tuning** = Customizing it with your business logic and domain rules
- **QLoRA** = A technique that makes fine-tuning memory-efficient (like using a lightweight ORM instead of loading everything into memory)

### Tech Stack Explained

| Technology | What It Is | Why We Use It |
|-----------|-----------|--------------|
| **Qwen2.5-1.5B** | A 1.5 billion parameter LLM by Alibaba | Small enough for free GPU, Apache 2.0 license |
| **QLoRA** | Quantized Low-Rank Adaptation | Reduces GPU memory from 12 GB to 6 GB |
| **Unsloth** | Training optimization library | Makes training 2x faster |
| **TRL** | Transformers Reinforcement Learning | Provides SFTTrainer for supervised fine-tuning |
| **PEFT** | Parameter-Efficient Fine-Tuning | Implements LoRA adapters |
| **BitsAndBytes** | Quantization library | Compresses model to 4-bit for training |
| **Google Colab** | Free GPU notebooks | T4 GPU with 15 GB VRAM |
| **HuggingFace** | Model hosting platform | Free model hosting and community |
| **FastAPI** | Python web framework | High-performance API backend |
| **Next.js** | React framework | Frontend with Vercel deployment |

---

## 2. Phase 1: Project Setup

### Goal
Create the repository structure and set up version control.

### What We Did
```bash
# Created the directory structure
transit-foundation-model/
├── datasets/      # Where GTFS data lives
├── notebooks/     # Jupyter notebooks for exploration
├── training/      # Model training code
├── evaluation/    # Model evaluation code
├── inference/     # Code to run the model
├── docs/          # Documentation
├── scripts/       # Python pipeline scripts
├── app/           # Web application
└── README.md
```

### Why This Structure?
Each directory has a clear purpose, following ML project conventions. This separation makes it easy to find code, and `.gitkeep` files ensure empty directories are tracked by Git.

### Key Files Created
- `.gitignore` — Excludes large files (raw GTFS data, model checkpoints, `node_modules/`) from Git
- `pyproject.toml` — Modern Python project configuration (PEP 621) with dependencies

### Concept: pyproject.toml
In Java you have `pom.xml` (Maven) or `build.gradle`. In Python, `pyproject.toml` is the modern equivalent. It defines:
- Project name, version, description
- Python version requirement (`>=3.10` for Colab compatibility)
- Dependencies (pandas, requests, etc.)
- Tool configurations (ruff linter, pytest)

---

## 3. Phase 2: GTFS Dataset Collection

### Goal
Download publicly available GTFS feeds from transit agencies worldwide.

### Concepts

**Mobility Database**: A free, open catalog of 6,000+ GTFS feeds from transit agencies in 72+ countries. We download their CSV catalog (no API key needed) and select feeds from it.

**Data Provenance**: For ML training, you must track where every piece of data came from, when it was downloaded, its license, and its integrity (SHA256 hash). This is like audit logging in enterprise systems.

### How It Works

```
Mobility Database CSV → Filter → Select 15 diverse feeds → Download ZIPs → Validate → Store with metadata
```

### Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/config.py` | Central configuration — all paths, constants, and logging setup in one place |
| `scripts/catalog_builder.py` | Downloads the Mobility Database CSV and filters to usable GTFS feeds |
| `scripts/feed_selector.py` | Selects 15 diverse feeds (large/medium/small, different countries) |
| `scripts/download_feeds.py` | Downloads each feed with retry logic, progress bars, and SHA256 checksums |
| `scripts/validate_feed.py` | Validates GTFS ZIP structure (required files present, CSVs parseable) |

### Key Design Decisions

**Why 15 feeds?** Enough diversity (10 countries, 3 size categories) without overwhelming the pipeline. More feeds = more training data but also more processing time.

**Why sequential downloads?** Being polite to transit agency servers. Parallel downloads could get us blocked.

**Why store metadata.json per feed?** Full provenance tracking. Each feed has a JSON file recording download URL, timestamp, SHA256, license, validation status.

### Commands
```bash
python -m scripts.catalog_builder    # Download catalog (2,000+ feeds)
python -m scripts.feed_selector      # Select 15 diverse feeds → seed_feeds.json
python -m scripts.download_feeds     # Download all feeds (~858 MB)
```

### Output
```
datasets/raw/
  mdb-29/gtfs.zip + metadata.json     # LA Metro (US)
  mdb-389/gtfs.zip + metadata.json    # Chicago CTA (US)
  mdb-782/gtfs.zip + metadata.json    # Berlin VBB (DE)
  ... (15 feeds total)
```

---

## 4. Phase 3: Data Cleaning

### Goal
Parse raw GTFS ZIPs into normalized Parquet files with consistent schemas.

### The Problem
Each transit agency uses slightly different column names, orderings, and optional fields:
- Austin's `stops.txt` has 17 columns; Chicago's has 9
- Some feeds have leading spaces in column names (` stop_id` vs `stop_id`)
- The Netherlands feed has 17 million rows in `stop_times.txt` — can't load into memory at once

### Concepts

**Parquet**: A columnar file format (like a database table stored as a file). Much faster and smaller than CSV. Think of it as the difference between reading a book page-by-page (CSV) vs having an index (Parquet).

**Schema normalization**: Like database schema migration — we define the canonical column set for each GTFS file and transform all feeds to match it.

**Chunked processing**: For files too large to fit in memory (17M rows), we process them in 500,000-row chunks using PyArrow's row-group feature.

### Scripts Created

| Script | Purpose |
|--------|---------|
| `scripts/gtfs_schema.py` | Defines canonical columns, dtypes, and primary keys for all 11 GTFS file types |
| `scripts/clean_feed.py` | Cleans one feed: parse CSV → normalize columns → coerce types → deduplicate → check integrity → write Parquet |
| `scripts/clean_all_feeds.py` | Orchestrator that cleans all 15 feeds and generates a report |

### The Cleaning Pipeline (per file)

```
1. Read CSV from ZIP (handle UTF-8-BOM encoding)
2. Strip whitespace from column names
3. Keep only canonical GTFS columns, drop agency-specific extensions
4. Add missing required columns as NA
5. Coerce data types (IDs→string, coordinates→float64, enums→Int8)
6. Remove duplicate rows by primary key
7. Write to Parquet with snappy compression
```

### Key Design Decisions

**Why keep IDs as strings?** GTFS IDs like `stop_id` can look numeric ("12345") but are actually identifiers. Converting to integers loses leading zeros and breaks joins.

**Why keep times as strings?** GTFS allows times > 24:00:00 (e.g., "25:30:00" means 1:30 AM the next day). Parsing as datetime would fail.

**Why Parquet not CSV?** Parquet is 3-10x smaller, supports column-level reads (don't load what you don't need), and preserves data types.

### Referential Integrity Checks
Like database foreign key constraints:
- Every `trip_id` in stop_times must exist in trips
- Every `route_id` in trips must exist in routes
- Every `stop_id` in stop_times must exist in stops
- Every `service_id` in trips must exist in calendar/calendar_dates

### Commands
```bash
python -m scripts.clean_all_feeds    # Clean all 15 feeds → Parquet
```

### Output
- 15 cleaned feed directories with Parquet files
- `cleaning_report.json` with aggregate statistics
- **11,178 routes, 296,066 stops, 2,981,396 trips, 77,388,649 stop_times**

---

## 5. Phase 4: Synthetic Dataset Generation

### Goal
Create instruction/response training pairs from the cleaned GTFS data.

### The Key Insight

**The model doesn't train on raw GTFS data.** We use the GTFS data to *generate* thousands of question/answer pairs. Think of it like this:
- Raw GTFS = your production database
- Training dataset = the documentation you'd write about that database
- The model learns from the documentation, not the raw tables

### Two-Stage Pipeline

**Stage 1 — Pre-compute statistics** (`precompute_feed_stats.py`):
Extracts per-feed summaries from Parquet into lightweight JSON. This avoids loading 77M rows during Q&A generation.

For each feed, computes: route counts by type, trip counts per route, first/last departure times, stop counts, transfer summaries.

**Memory strategy for large files:** Build a `trip_id → route_id` mapping from trips.parquet (fits in memory), then scan stop_times.parquet row-group by row-group using PyArrow, accumulating statistics incrementally. Peak memory stays under 300 MB even for the 17M-row Netherlands feed.

**Stage 2 — Generate Q&A pairs** (`generate_synthetic_dataset.py`):
Reads the pre-computed summaries, applies question templates across 8 categories, writes JSONL.

### 8 Task Categories

| Category | Example | Count |
|----------|---------|-------|
| Agency Overview | "How many routes does CTA have?" → "133 routes..." | 1,075 |
| Route Information | "Describe route Red Line by CTA" → "A Subway/Metro service..." | 457 |
| Stop/Station Info | "Where is Clark & Belmont?" → "Located at (41.94, -87.65)" | 911 |
| Trip & Schedule | "What are the first/last departures for route 22?" → "5:00 AM to 1:30 AM" | 636 |
| Transfer Analysis | "What transfers exist at Union Station?" → "Recommended transfer..." | 161 |
| Network Statistics | "How large is the CTA network?" → "133 routes, 11,177 stops..." | 30 |
| GTFS Knowledge | "What does route_type 3 mean?" → "Bus service..." | 22 |
| Comparative | "Which agency has the most routes?" → "OVapi Netherlands (3,114)" | 14 |

### Question Templates

Each category has 2-5 template functions that take a fact dictionary and produce an instruction/response pair with varied phrasing:

```python
# Template generates different question styles for the same fact:
"How many routes does CTA have?"          # Direct
"Tell me about the size of CTA's network" # Indirect
"What transit modes does CTA operate?"    # Different angle
```

### JSONL Format

Each record in `train.jsonl`:
```json
{
  "instruction": "How many bus routes does the CTA operate?",
  "response": "The CTA operates 125 bus routes...",
  "category": "agency_overview",
  "template_id": "agency_route_count_v1",
  "feed_id": "389",
  "provider": "Chicago Transit Authority (CTA)"
}
```

### Commands
```bash
python -m scripts.precompute_feed_stats     # Extract feed statistics
python -m scripts.generate_synthetic_dataset --seed 42  # Generate Q&A pairs
```

### Output
- `datasets/synthetic/train.jsonl` — 3,306 instruction/response pairs
- `datasets/synthetic/generation_report.json` — category counts and metadata

---

## 6. Phase 5: Dataset Validation

### Goal
Verify dataset quality and create a train/test split.

### Validation Checks

| Check | What It Verifies | Result |
|-------|-----------------|--------|
| Format | All 6 required fields present in every record | PASS |
| Content Quality | No empty fields, responses > 20 chars | PASS |
| Duplicates | No duplicate instructions | PASS (0 found) |
| Distribution | Coverage across feeds and categories | PASS (15 feeds, 45 templates) |
| Factual Accuracy | Numbers in responses match source data | PASS (275/275 = 100%) |

### Stratified Train/Test Split

We split 90/10 by category (not randomly) to ensure every category is represented in both sets:
- **Train:** 2,971 pairs
- **Test:** 335 pairs

### Why Stratified?
If we split randomly, rare categories like "comparative" (14 pairs) might end up entirely in train or test. Stratified splitting guarantees proportional representation.

### Commands
```bash
python -m scripts.validate_dataset --seed 42
```

---

## 7. Phase 6: Base Model Selection

### Goal
Choose which pre-trained model to fine-tune.

### Candidates Evaluated

| Model | Params | License | Context | Why Considered |
|-------|--------|---------|---------|---------------|
| **Qwen2.5-1.5B** | 1.54B | Apache 2.0 | 32K | Best multilingual, strong instruction-following |
| SmolLM2-1.7B | 1.7B | Apache 2.0 | 4-8K | Fastest inference |
| Llama-3.2-1B | 1.26B | Llama License | 8K | Largest community |
| Gemma-3-1B | 1.0B | Apache 2.0 | 8K | Best math/reasoning |

### Why Qwen2.5-1.5B-Instruct?

1. **Apache 2.0 license** — required for open-source publishing
2. **32K context** — longest among candidates
3. **29 languages** — our data spans 10 countries
4. **Strong instruction-following** — already tuned for Q&A
5. **~6 GB VRAM with QLoRA** — fits Google Colab's free T4 (15 GB)

### Concept: QLoRA

Traditional fine-tuning updates all 1.5 billion parameters — needs 24+ GB VRAM. QLoRA makes it feasible on a free GPU:

1. **Quantization (Q)**: Compress the model from 16-bit to 4-bit (75% memory savings)
2. **Low-Rank Adaptation (LoRA)**: Instead of updating all parameters, add small trainable "adapter" matrices to key layers. Only ~1-2% of parameters are trainable.

**Analogy**: Instead of rebuilding an entire Spring Boot application (full fine-tuning), you add a few custom interceptors and filters (LoRA adapters) that modify the behavior at key points.

### Configuration

```python
# LoRA settings (in scripts/model_config.py)
r = 16           # Rank — size of adapter matrices
lora_alpha = 32  # Scaling factor (typically 2x rank)
lora_dropout = 0 # Must be 0 for 4-bit with Unsloth
target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",  # Attention
                   "gate_proj", "up_proj", "down_proj"]     # MLP
```

**What are target_modules?** In a transformer model, each layer has attention modules (q/k/v/o projections) and MLP modules (gate/up/down projections). LoRA adds trainable adapters to these specific modules. Think of them as the "hot spots" where domain knowledge is encoded.

---

## 8. Phase 7: QLoRA Training

### Goal
Fine-tune the model on Google Colab with the synthetic dataset.

### Notebook: `training/train_umartransit.ipynb`

This runs on Google Colab (free T4 GPU). The notebook is self-contained — it installs dependencies, downloads the model, trains, evaluates, and uploads to HuggingFace.

### Training Configuration

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| Epochs | 3 | Number of times the model sees all training data |
| Batch size | 4 | Samples processed at once (limited by GPU memory) |
| Gradient accumulation | 4 | Simulates batch size 16 by accumulating 4 mini-batches |
| Learning rate | 2e-4 | How much to update weights per step (0.0002) |
| Scheduler | Cosine | Learning rate decreases following a cosine curve |
| Warmup | 3% | Gradually increase LR for first 3% of steps |
| Optimizer | AdamW 8-bit | Memory-efficient optimizer |
| Max sequence length | 1024 | Maximum tokens per training example |

### Chat Template

Qwen2.5 uses a specific format for conversations:
```
<|im_start|>system
You are UmarTransit-1B...<|im_end|>
<|im_start|>user
What does route_type 3 mean?<|im_end|>
<|im_start|>assistant
In the GTFS specification, route_type 3 indicates Bus service...<|im_end|>
```

The training data is formatted into this template before training so the model learns to follow instructions in this format.

### Key Issues Encountered & Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `evaluation_strategy` TypeError | Renamed in newer transformers | Use `eval_strategy` |
| PicklingError with TrainingArguments | Unsloth patches TRL classes | Use `SFTConfig` instead of `TrainingArguments` |
| `lora_dropout` causes errors | Must be 0 for 4-bit quantization | Set `lora_dropout=0` |
| `dataset_num_proc` crash | Parameter moved in newer TRL | Remove from SFTTrainer |

### How to Run
1. Open `training/train_umartransit.ipynb` in Google Colab
2. Set runtime to **T4 GPU** (Runtime → Change runtime type)
3. **Runtime → Run all**
4. Login to HuggingFace when prompted (Cell 11)
5. Training takes ~30-60 minutes

---

## 9. Phase 8: Evaluation

### Goal
Quantify model performance on the 335-pair test set.

### Notebook: `evaluation/evaluate_umartransit.ipynb`

Runs on Google Colab (T4 GPU). Loads the model from HuggingFace, generates responses for all test pairs, and computes metrics.

### Metrics Explained

**ROUGE-L (0.8192)**: Measures the longest common subsequence between expected and generated responses. Score of 0.82 means the model's responses share ~82% of the content structure with expected answers. This is excellent for a 1.5B model.

**Keyword Match (0.4086)**: Checks if specific numbers and facts from expected answers appear in generated answers. Score of 0.41 means the model gets ~41% of exact numbers right — it understands patterns but sometimes generates wrong specific values (e.g., wrong coordinates, wrong route counts).

### Per-Category Results

| Category | Strength/Weakness | Why |
|----------|------------------|-----|
| Transfer (0.90) | Best | Formulaic answers, easy patterns |
| Agency overview | Strong | Template-based, well-represented in training |
| GTFS knowledge (0.38) | Weakest | Only 22 training pairs — too few |

### What the Model Gets Right
- GTFS concepts (route types, file relationships)
- Agency-level facts (route counts, modes)
- Timezone and transfer information

### What the Model Gets Wrong
- Specific coordinates (close but not exact)
- Exact route lists (sometimes hallucinates route numbers)
- Some GTFS spec details (invents non-existent files)

---

## 10. Phase 9: Model Optimization

### Goal
Create optimized model variants and a proper HuggingFace model card.

### Model Card (`docs/MODEL_CARD.md`)
A model card is like API documentation for your model. It tells users:
- What the model does and doesn't do
- How it was trained (base model, data, hyperparameters)
- Evaluation results
- Usage examples (Python code, Ollama commands)
- Limitations and ethical considerations

### GGUF Export (`inference/export_gguf.ipynb`)
GGUF is a model format optimized for CPU inference (used by llama.cpp and Ollama). Converting to GGUF with 4-bit quantization reduces the model from 3 GB to ~1 GB while maintaining most quality.

**Note:** This requires Colab GPU time. If GPU quota is exhausted, the model still runs via Transformers (just slower).

---

## 11. Phase 10: HuggingFace Publishing

### Goal
Publish the model for public use.

The model was published during Phase 7 training (Cell 11 of the training notebook calls `push_to_hub_merged`). The model card was updated in Phase 9.

### Model URL
**https://huggingface.co/umarfarookm/UmarTransit-1B**

### What's Published
- Model weights in safetensors format (3.1 GB, BF16)
- Tokenizer files
- Chat template
- Model card (README.md)

---

## 12. Phase 11: Local Inference

### Goal
Run UmarTransit-1B on your own machine.

### Script: `inference/run_local.py`

Two modes:
```bash
# Interactive chat
python -m inference.run_local

# Single question
python -m inference.run_local -q "What is GTFS?"
```

### How It Works

1. Downloads model from HuggingFace (~3 GB, cached after first run)
2. Loads into RAM as float32 (CPU inference)
3. Applies Qwen2.5 chat template
4. Generates response token by token

### Performance
- First load: ~90 seconds (downloading model)
- Subsequent loads: ~7 seconds (cached)
- Generation speed: ~2 tokens/second on Intel CPU
- Memory usage: ~4-5 GB RAM

---

## 13. Phase 12: Web Application

### Goal
Build a web interface for the model.

### Architecture

```
Next.js Frontend (Vercel)  ←→  FastAPI Backend (local Mac)
  - Chat UI                      - Loads model once
  - Demo mode (pre-computed)      - /api/chat endpoint
  - Live mode (calls API)         - ~20s per response
  - Mobile responsive
```

### Frontend: `app/web/`

Built with Next.js + Tailwind CSS. Two modes:

**Demo Mode** (default): Shows pre-computed answers from the actual model. Works without any backend — anyone can use it. Perfect for showcasing the model's capabilities.

**Live Mode**: Connects to a local FastAPI backend running on your machine. Real-time model inference with any question.

### Backend: `app/api/main.py`

FastAPI server that:
1. Loads UmarTransit-1B at startup
2. Exposes `POST /api/chat` endpoint
3. Accepts `{"question": "..."}`, returns `{"answer": "...", "tokens": N, "time_seconds": T}`
4. CORS enabled for cross-origin frontend calls

### Running Locally

**Terminal 1 — Backend:**
```bash
.venv/bin/uvicorn app.api.main:app --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd app/web
npm install
npm run dev
```

Open http://localhost:3000

### Deployment

- **Frontend:** Deployed to Vercel (free) at `transit-foundation-model.vercel.app`
- **Backend:** Runs locally on your machine (free GPU/CPU hosting platforms don't have enough RAM for a 3 GB model)

### Why Not Full Cloud Deployment?

The model is 3 GB — it needs 4-6 GB RAM to run. Free tiers of cloud platforms (Railway 512 MB, Render 512 MB, HF Spaces needs PRO) don't provide enough. Options for future:
- Oracle Cloud free tier (24 GB RAM, always free)
- HuggingFace PRO ($9/month)
- HuggingFace Inference Endpoints (~$0.06/hr)

---

## 14. Future Improvements

### More Training Data
- Increase from 3,306 to 10,000+ pairs
- Add more GTFS knowledge pairs (currently only 22)
- Add Indian city feeds (Chennai, Bangalore, Mumbai)

### Better Model
- Try larger base models (Qwen2.5-3B, Qwen2.5-7B) when GPU access allows
- Use DPO (Direct Preference Optimization) for response quality
- Add GTFS-Realtime understanding

### Better Evaluation
- Human evaluation alongside automated metrics
- Task-specific benchmarks (coordinate accuracy, route list accuracy)
- A/B testing against base model

### Production Deployment
- Deploy backend to Oracle Cloud free tier
- Add rate limiting and authentication
- Stream responses (token-by-token output)
- GGUF conversion for Ollama deployment

---

## Key Learnings

1. **Data quality > data quantity**: 3,306 well-structured pairs achieved 0.82 ROUGE-L. Noisy data would have been worse.

2. **QLoRA democratizes fine-tuning**: A $0 Google Colab account can train a 1.5B parameter model. You don't need expensive hardware.

3. **Version conflicts are real**: Unsloth, TRL, and Transformers evolve rapidly. Always use the exact versions that work together.

4. **Small models hallucinate specific details**: The model understands patterns but invents specific numbers. This is inherent to 1.5B models with small training sets.

5. **Free tier has limits**: HuggingFace, Google Colab, and cloud platforms all have restrictions. Plan around them.

---

*Built by [umarfarookm](https://github.com/umarfarookm) as a learning project in AI/ML engineering.*
