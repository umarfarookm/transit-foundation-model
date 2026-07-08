"""Local inference for UmarTransit-1B using Transformers (CPU).

Run interactively:
    python -m inference.run_local

Or with a single question:
    python -m inference.run_local --question "What does route_type 3 mean in GTFS?"
"""

import argparse
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "umarfarookm/UmarTransit-1B"
MAX_NEW_TOKENS = 256

SYSTEM_PROMPT = (
    "You are UmarTransit-1B, a specialized AI assistant for public transit systems "
    "and GTFS (General Transit Feed Specification) data. You provide accurate, "
    "detailed answers about transit routes, stops, schedules, transfers, and GTFS concepts."
)


def load_model() -> tuple:
    """Load the model and tokenizer from HuggingFace."""
    print(f"Loading {MODEL_ID}...")
    print("(First run downloads ~3 GB, subsequent runs use cache)")
    start = time.time()

    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float32,  # CPU needs float32
        device_map="cpu",
    )
    model.eval()

    elapsed = time.time() - start
    print(f"Model loaded in {elapsed:.1f}s")
    return model, tokenizer


def ask(model, tokenizer, question: str) -> str:
    """Generate a response for a question."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt")
    input_len = inputs["input_ids"].shape[-1]

    start = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.1,
            top_p=0.9,
            do_sample=True,
        )
    elapsed = time.time() - start

    response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
    tokens_generated = outputs.shape[-1] - input_len
    print(f"  ({tokens_generated} tokens in {elapsed:.1f}s, {tokens_generated/elapsed:.1f} tok/s)")

    return response


def interactive_mode(model, tokenizer) -> None:
    """Run an interactive chat loop."""
    print("\n" + "=" * 60)
    print("UmarTransit-1B — Local Inference (CPU)")
    print("=" * 60)
    print("Type your transit/GTFS questions. Type 'quit' to exit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        response = ask(model, tokenizer, question)
        print(f"\nUmarTransit: {response}\n")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="UmarTransit-1B Local Inference")
    parser.add_argument("--question", "-q", type=str, help="Single question (non-interactive)")
    args = parser.parse_args()

    model, tokenizer = load_model()

    if args.question:
        response = ask(model, tokenizer, args.question)
        print(f"\n{response}")
    else:
        interactive_mode(model, tokenizer)


if __name__ == "__main__":
    main()
