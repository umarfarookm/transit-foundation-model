"""Base model selection and training configuration for UmarTransit-1B.

Model Selection Decision (Phase 6)
====================================

Chosen: Qwen2.5-1.5B-Instruct
Alternatives considered: SmolLM2-1.7B, Llama-3.2-1B, Gemma-3-1B

Selection criteria:
  - Apache 2.0 license (required for open-source publishing)
  - ~1B parameters (fits "UmarTransit-1B" naming)
  - QLoRA-compatible on Google Colab free T4 GPU (15GB VRAM)
  - Multilingual support (dataset covers 10 countries)
  - Strong instruction-following from pre-training
  - Proven fine-tuning quality on small datasets (~3K pairs)

Why Qwen2.5-1.5B over alternatives:
  - 32K context window (vs 4-8K for others)
  - 29 languages (critical for global transit feeds)
  - Apache 2.0 license (Llama-3.2 uses Llama license)
  - Better multilingual benchmarks than SmolLM2/Gemma-3
  - Well-supported by HuggingFace Transformers + PEFT + TRL

Training environment: Google Colab (free tier, T4 GPU, 15GB VRAM)
Estimated VRAM usage: ~6-8 GB with QLoRA 4-bit
Estimated training time: 2-4 hours on T4
"""

# ── Base Model ─────────────────────────────────────────────────────────────────

BASE_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_NAME = "UmarTransit-1B"
MODEL_REVISION = "main"

# Fallback model if primary has issues
FALLBACK_MODEL_ID = "HuggingFaceTB/SmolLM2-1.7B-Instruct"

# ── QLoRA Configuration ───────────────────────────────────────────────────────

QLORA_CONFIG = {
    "r": 16,                      # LoRA rank — 16 is good for small models
    "lora_alpha": 32,             # Scaling factor — typically 2x rank
    "lora_dropout": 0.05,         # Light dropout for regularization
    "bias": "none",               # No bias adaptation
    "task_type": "CAUSAL_LM",     # Causal language modeling
    "target_modules": [           # Qwen2.5 attention + MLP modules
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
}

# ── BitsAndBytes Quantization ──────────────────────────────────────────────────

QUANTIZATION_CONFIG = {
    "load_in_4bit": True,
    "bnb_4bit_quant_type": "nf4",           # NormalFloat4 quantization
    "bnb_4bit_compute_dtype": "bfloat16",   # Compute in bfloat16
    "bnb_4bit_use_double_quant": True,      # Double quantization for memory savings
}

# ── Training Hyperparameters ───────────────────────────────────────────────────

TRAINING_CONFIG = {
    "num_train_epochs": 3,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,   # Effective batch size = 16
    "learning_rate": 2e-4,
    "weight_decay": 0.01,
    "warmup_ratio": 0.03,
    "lr_scheduler_type": "cosine",
    "max_seq_length": 1024,             # Sufficient for our Q&A pairs
    "logging_steps": 10,
    "save_strategy": "epoch",
    "fp16": False,                      # Use bf16 instead on T4
    "bf16": True,
    "optim": "paged_adamw_8bit",        # Memory-efficient optimizer
    "seed": 42,
}

# ── Dataset Configuration ──────────────────────────────────────────────────────

DATASET_CONFIG = {
    "train_file": "datasets/synthetic/train.jsonl",
    "test_file": "datasets/synthetic/test.jsonl",
    "instruction_field": "instruction",
    "response_field": "response",
    "max_seq_length": 1024,
}

# ── Output ─────────────────────────────────────────────────────────────────────

OUTPUT_MODEL_DIR = "training/output"
HF_REPO_ID = "umarfarookm/UmarTransit-1B"
