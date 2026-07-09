# HuggingFace Forum Post

**Post this at:** https://discuss.huggingface.co/c/show-and-tell/65

**Title:** UmarTransit-1B: First Open-Source Transit Domain LLM (Fine-tuned Qwen2.5-1.5B)

**Copy everything below this line:**

---

Hi everyone!

I'm sharing **UmarTransit-1B** — a domain-specific language model fine-tuned for public transit systems and GTFS (General Transit Feed Specification) data.

[Model on HuggingFace](https://huggingface.co/umarfarookm/UmarTransit-1B) | [GitHub](https://github.com/umarfarookm/transit-foundation-model)

## What is it?

A QLoRA fine-tuned version of Qwen2.5-1.5B-Instruct that specializes in GTFS specification knowledge, transit route/schedule analysis, stop/station information across 10 countries, and transfer connections.

**Available formats:**
- Safetensors (3.09 GB) — for Transformers/Python
- GGUF Q4_K_M (986 MB) — for Ollama/llama.cpp (recommended for local use)
- GGUF Q8_0 (1.65 GB) — for Ollama/llama.cpp (higher quality)

## How it was built

I'm a Senior Technical Lead (Java/Spring Boot, 12+ years) experienced with LLM APIs (OpenAI, Claude) and GTFS/transit systems. This is my first end-to-end model training project — from data collection to fine-tuning to deployment. Built the entire pipeline:

1. Collected 15 public GTFS feeds from 10 countries (858 MB raw data)
2. Cleaned 77M+ rows into normalized Parquet files
3. Generated 3,306 synthetic instruction/response pairs across 8 task categories
4. Fine-tuned Qwen2.5-1.5B-Instruct with QLoRA using Unsloth on Google Colab (free T4)
5. Evaluated: ROUGE-L 0.82, best category Transfer (0.90)
6. Exported to GGUF (Q4_K_M and Q8_0) for local inference
7. Deployed frontend to Vercel, model to HuggingFace

Training: QLoRA rank=16, alpha=32, 3 epochs, ~30 min on Colab T4, Unsloth + TRL SFTTrainer

## Example outputs

Q: What does route_type 3 mean in GTFS?
A: In the GTFS specification, route_type 3 indicates Bus service. This is the most common route type and covers short- and long-distance bus routes.

Q: How many routes does the Chicago Transit Authority operate?
A: The Chicago Transit Authority (CTA) operates 133 routes. 8 are Subway/Metro routes and 125 are Bus routes.

Q: Can GTFS times exceed 24:00:00?
A: Yes, GTFS allows times greater than 24:00:00 in stop_times.txt. This is used for trips that extend past midnight relative to the service day.

## What I learned

- QLoRA makes fine-tuning accessible on free hardware (Colab T4, 15GB VRAM)
- 3,306 well-structured training pairs achieved 0.82 ROUGE-L — data quality matters more than quantity
- 1.5B models can learn domain patterns well but hallucinate specific details
- GGUF Q4_K_M reduces the model from 3 GB to under 1 GB with minimal quality loss

## Future plans

- Add Indian city transit feeds (Chennai, Bangalore, Mumbai)
- Increase training data to 10K+ pairs
- Add more GTFS spec knowledge pairs

The entire project is open source (Apache 2.0) with a detailed build guide for engineers new to AI/ML. Feedback and contributions welcome!
