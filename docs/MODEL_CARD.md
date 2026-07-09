---
license: apache-2.0
base_model: Qwen/Qwen2.5-1.5B-Instruct
tags:
  - transit
  - gtfs
  - transportation
  - instruction-following
  - qwen2
  - qlora
  - unsloth
language:
  - en
dataset_info:
  dataset_name: UmarTransit Synthetic Q&A
pipeline_tag: text-generation
---

# UmarTransit-1B

A domain-specific language model for **public transit systems** and **GTFS (General Transit Feed Specification)** data, fine-tuned from Qwen2.5-1.5B-Instruct.

UmarTransit-1B specializes in:
- GTFS understanding and validation
- Transit route and schedule analysis
- Stop/station information
- Transfer optimization
- Transit network statistics
- Cross-agency comparisons

> **Data Disclaimer:** This model was trained **exclusively on publicly available, open-source GTFS feeds** published by transit agencies for public use via the [Mobility Database](https://mobilitydatabase.org/). **No private, proprietary, or NDA-protected data** from any client, employer, or organization was used at any stage.

## Model Details

| Property | Value |
|----------|-------|
| **Base Model** | [Qwen/Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) |
| **Parameters** | 1.54B (1.31B non-embedding) |
| **Fine-tuning** | QLoRA (4-bit NF4, LoRA rank=16, alpha=32) |
| **Training Framework** | [Unsloth](https://unsloth.ai) + HuggingFace TRL |
| **Training Data** | 2,971 synthetic instruction-response pairs |
| **Test Data** | 335 pairs (stratified 90/10 split) |
| **Max Context** | 1,024 tokens |
| **License** | Apache 2.0 |
| **Developer** | [umarfarookm](https://github.com/umarfarookm) |

## Evaluation Results

Evaluated on 335 held-out test pairs across 8 task categories:

| Metric | Score |
|--------|-------|
| **ROUGE-L** | 0.8192 |
| **Keyword Match** | 0.4086 |

**Best performing:** Transfer analysis (ROUGE-L: 0.90)
**Needs improvement:** GTFS knowledge (ROUGE-L: 0.38) — limited training data (22 pairs)

## Available Formats

| Format | File | Size | Use Case |
|--------|------|------|----------|
| Safetensors | `model.safetensors` | 3.09 GB | Full precision — Transformers/Python |
| GGUF Q4_K_M | `UmarTransit-1B.Q4_K_M.gguf` | 986 MB | 4-bit — Ollama/llama.cpp (recommended) |
| GGUF Q8_0 | `UmarTransit-1B.Q8_0.gguf` | 1.65 GB | 8-bit — Ollama/llama.cpp (higher quality) |

## Training Data

The model was trained on synthetic instruction-response pairs generated from **15 real public GTFS feeds** across **10 countries**:

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

**8 task categories:** Agency overview, route information, stop/station info, trip schedules, transfer analysis, network statistics, GTFS knowledge, comparative analysis.

## Usage

### With Transformers

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model = AutoModelForCausalLM.from_pretrained(
    "umarfarookm/UmarTransit-1B",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("umarfarookm/UmarTransit-1B")

messages = [
    {"role": "system", "content": "You are UmarTransit-1B, a specialized AI assistant for public transit systems and GTFS data."},
    {"role": "user", "content": "What does route_type 3 mean in GTFS?"},
]

text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(text, return_tensors="pt").to(model.device)

outputs = model.generate(**inputs, max_new_tokens=256, temperature=0.1, do_sample=True)
response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
print(response)
```

### With Ollama (GGUF)

```bash
# Download the GGUF file from this repo, then:
ollama create umartransit -f Modelfile
ollama run umartransit "What are the required files in a GTFS feed?"
```

## Training Configuration

```
QLoRA Config:
  rank: 16
  alpha: 32
  dropout: 0
  target_modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj

Training:
  epochs: 3
  batch_size: 4 x 4 gradient accumulation = 16 effective
  learning_rate: 2e-4
  scheduler: cosine
  optimizer: adamw_8bit
  hardware: Google Colab T4 GPU (15GB VRAM)
```

## Limitations

- **Small training dataset:** 2,971 pairs — model may hallucinate specific details (coordinates, exact counts)
- **Limited GTFS knowledge:** Only 22 GTFS specification Q&A pairs in training
- **English-primary:** Trained on English instructions, though base model supports 29 languages
- **Static data:** Trained on GTFS schedule data, not real-time transit information
- **Not a trip planner:** Cannot compute actual routes or real-time ETAs

## Future Improvements

- Add more GTFS knowledge pairs (target 100+)
- Include Indian city transit feeds (Chennai, Bangalore, Mumbai)
- Expand to 10K+ training pairs for better factual accuracy
- Add GTFS-Realtime understanding

## Source Code

[github.com/umarfarookm/transit-foundation-model](https://github.com/umarfarookm/transit-foundation-model)

## Citation

```bibtex
@misc{umartransit1b,
  title={UmarTransit-1B: A Domain-Specific Language Model for Public Transit},
  author={umarfarookm},
  year={2026},
  url={https://huggingface.co/umarfarookm/UmarTransit-1B}
}
```
