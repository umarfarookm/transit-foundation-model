# UmarTransit-1B

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Model on HF](https://img.shields.io/badge/Model-HuggingFace-yellow.svg)](https://huggingface.co/umarfarookm/UmarTransit-1B)
[![Demo](https://img.shields.io/badge/Demo-Vercel-black.svg)](https://transit-foundation-model.vercel.app)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![ROUGE-L](https://img.shields.io/badge/ROUGE--L-0.82-brightgreen.svg)]()
[![GGUF](https://img.shields.io/badge/GGUF-Available-orange.svg)](https://huggingface.co/umarfarookm/UmarTransit-1B)

A domain-specific foundation model for **public transit systems** and **GTFS (General Transit Feed Specification)** data, built from scratch as an end-to-end AI/ML engineering project.

> **Data Disclaimer:** This project uses **only publicly available, open-source GTFS feeds** published by transit agencies for public use via the [Mobility Database](https://mobilitydatabase.org/). **No private, proprietary, or NDA-protected data** from any client, employer, or organization was used at any stage — data collection, training, or evaluation. All data sources are documented in [`datasets/catalog/seed_feeds.json`](datasets/catalog/seed_feeds.json).

**Live Demo:** [transit-foundation-model.vercel.app](https://transit-foundation-model.vercel.app)
**Model:** [huggingface.co/umarfarookm/UmarTransit-1B](https://huggingface.co/umarfarookm/UmarTransit-1B)
**Documentation:** [Step-by-step build guide](docs/GUIDE.md)

## What It Does

UmarTransit-1B answers questions about:
- GTFS specification (file formats, field meanings, relationships)
- Transit routes, stops, and schedules from 15 agencies across 10 countries
- Transfer connections and network statistics
- Cross-agency comparisons

```
Q: What does route_type 3 mean in GTFS?
A: In the GTFS specification, route_type 3 indicates Bus service.
   This is the most common route type and covers short- and long-distance bus routes.

Q: How many routes does the Chicago Transit Authority operate?
A: The Chicago Transit Authority (CTA) operates 133 routes.
   8 are Subway/Metro routes and 125 are Bus routes.
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA PIPELINE                            │
│                                                                 │
│  GTFS Feeds (15)  →  Clean (Parquet)  →  Synthetic Q&A (3,306) │
│  10 countries         77M rows            8 task categories      │
│  858 MB raw           11K routes                                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MODEL TRAINING                           │
│                                                                 │
│  Base: Qwen2.5-1.5B-Instruct  →  QLoRA Fine-tuning (Unsloth)  │
│  License: Apache 2.0              Google Colab T4 GPU           │
│  1.54B parameters                  3 epochs, ~30 min            │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT                               │
│                                                                 │
│  HuggingFace Hub  ←→  FastAPI Backend  ←→  Next.js Frontend    │
│  Model hosting         Local inference      Vercel (free)       │
│                        CPU (~2 tok/s)       Demo + Live mode    │
└─────────────────────────────────────────────────────────────────┘
```

## Evaluation Results

| Metric | Score |
|--------|-------|
| ROUGE-L | 0.8192 |
| Keyword Match | 0.4086 |
| Best Category | Transfer (0.90) |
| Test Pairs | 335 |

## Model Formats

| Format | File | Size | Use Case |
|--------|------|------|----------|
| Safetensors | `model.safetensors` | 3.09 GB | Full precision — Transformers/Python |
| GGUF Q4_K_M | `UmarTransit-1B.Q4_K_M.gguf` | 986 MB | 4-bit quantized — Ollama/llama.cpp (recommended) |
| GGUF Q8_0 | `UmarTransit-1B.Q8_0.gguf` | 1.65 GB | 8-bit quantized — Ollama/llama.cpp (higher quality) |

All formats available at [huggingface.co/umarfarookm/UmarTransit-1B](https://huggingface.co/umarfarookm/UmarTransit-1B)

## Project Structure

```
transit-foundation-model/
├── scripts/                    # Data & training pipeline
│   ├── config.py               # Paths, constants, logging
│   ├── catalog_builder.py      # Download Mobility Database catalog
│   ├── feed_selector.py        # Select diverse GTFS feeds
│   ├── download_feeds.py       # Download GTFS ZIPs with provenance
│   ├── validate_feed.py        # GTFS ZIP validation
│   ├── gtfs_schema.py          # Canonical GTFS schema definitions
│   ├── clean_feed.py           # Single-feed cleaning pipeline
│   ├── clean_all_feeds.py      # Clean all feeds orchestrator
│   ├── precompute_feed_stats.py # Extract feed statistics
│   ├── question_templates.py   # 8 Q&A categories, 45 templates
│   ├── generate_synthetic_dataset.py  # Generate train.jsonl
│   ├── validate_dataset.py     # Validate & split dataset
│   ├── model_config.py         # Model selection & hyperparameters
│   └── generate_model_card.py  # HuggingFace model card
├── datasets/
│   ├── catalog/seed_feeds.json # Curated feed list (15 feeds)
│   └── synthetic/              # Training data
│       ├── train.jsonl         # 2,971 training pairs
│       └── test.jsonl          # 335 test pairs
├── training/
│   └── train_umartransit.ipynb # QLoRA training notebook (Colab)
├── evaluation/
│   └── evaluate_umartransit.ipynb  # Evaluation notebook (Colab)
├── inference/
│   ├── run_local.py            # Local CPU inference script
│   └── export_gguf.ipynb       # GGUF export notebook (Colab)
├── app/
│   ├── api/main.py             # FastAPI backend
│   └── web/                    # Next.js frontend (Vercel)
├── docs/
│   ├── MODEL_CARD.md           # HuggingFace model card
│   └── GUIDE.md                # Step-by-step build guide
├── notebooks/
│   └── 01_explore_catalog.ipynb # GTFS catalog exploration
├── pyproject.toml              # Python project config
└── README.md
```

## Quick Start

### Prerequisites
- Python 3.10+ (3.12 recommended)
- Node.js 18+ (for frontend)
- Google Colab account (for training)
- HuggingFace account (for model hosting)

### 1. Clone & Setup
```bash
git clone https://github.com/umarfarookm/transit-foundation-model.git
cd transit-foundation-model
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install torch transformers accelerate fastapi uvicorn "huggingface-hub<1.0"
```

### 2. Run the Data Pipeline
```bash
source .venv/bin/activate

# Download GTFS feeds (15 feeds, ~858 MB)
.venv/bin/python -m scripts.catalog_builder
.venv/bin/python -m scripts.feed_selector
.venv/bin/python -m scripts.download_feeds

# Clean and normalize
.venv/bin/python -m scripts.clean_all_feeds

# Generate synthetic training data
.venv/bin/python -m scripts.precompute_feed_stats
.venv/bin/python -m scripts.generate_synthetic_dataset

# Validate and split
.venv/bin/python -m scripts.validate_dataset
```

### 3. Train the Model
Open `training/train_umartransit.ipynb` in Google Colab with a T4 GPU and run all cells.

### 4. Run Locally
```bash
# Terminal inference
.venv/bin/python -m inference.run_local

# Web interface (backend — Terminal 1)
.venv/bin/uvicorn app.api.main:app --port 8000

# Web interface (frontend — Terminal 2)
cd app/web && npm install && npm run dev
# Open http://localhost:3000
```

## Training Data Coverage

| Country | Agencies |
|---------|----------|
| US | LA Metro, Chicago CTA, Boston MBTA, Valley Metro, Capital Metro, TriMet |
| Canada | Toronto TTC |
| Germany | Berlin VBB |
| France | Ile-de-France Mobilites (Paris) |
| Netherlands | OVapi (national) |
| Belgium | NMBS/SNCB Railways |
| Finland | HSL Helsinki |
| Denmark | Rejseplanen |
| Australia | Transperth (Perth) |
| New Zealand | Auckland Transport |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Base Model | Qwen2.5-1.5B-Instruct |
| Fine-tuning | QLoRA + Unsloth + TRL |
| Training Hardware | Google Colab (T4 GPU) |
| Data Processing | pandas, PyArrow, Parquet |
| Backend | FastAPI + Uvicorn |
| Frontend | Next.js + Tailwind CSS |
| Model Hosting | HuggingFace Hub |
| Web Hosting | Vercel |

## Contributing

Contributions are welcome! Some ideas:

- **Add more GTFS feeds** — especially from Asia, Africa, South America
- **Improve training data** — more GTFS knowledge pairs, better question variety
- **Add new question categories** — fare information, accessibility, real-time data
- **Optimize inference** — GGUF conversion, model quantization
- **Improve the web app** — streaming responses, conversation history

See [docs/GUIDE.md](docs/GUIDE.md) for how the project is structured.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Documentation

See [docs/GUIDE.md](docs/GUIDE.md) for the complete step-by-step build guide covering all 12 phases with detailed explanations.

## Star History

If you find this project useful or interesting, please give it a star! It helps others discover it.

[![GitHub stars](https://img.shields.io/github/stars/umarfarookm/transit-foundation-model?style=social)](https://github.com/umarfarookm/transit-foundation-model)
