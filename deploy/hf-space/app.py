"""UmarTransit-1B API — HuggingFace Spaces (Gradio SDK).

Serves both a Gradio chat UI and a FastAPI /api/chat endpoint.
Free on HuggingFace Spaces (Gradio SDK, cpu-basic).
"""

import time

import gradio as gr
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "umarfarookm/UmarTransit-1B"
MAX_NEW_TOKENS = 256

SYSTEM_PROMPT = (
    "You are UmarTransit-1B, a specialized AI assistant for public transit systems "
    "and GTFS (General Transit Feed Specification) data. You provide accurate, "
    "detailed answers about transit routes, stops, schedules, transfers, and GTFS concepts."
)

print(f"Loading {MODEL_ID}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    device_map="cpu",
)
model.eval()
print("Model loaded!")


def ask(question: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt")
    input_len = inputs["input_ids"].shape[-1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.1,
            top_p=0.9,
            do_sample=True,
        )

    response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True).strip()
    return response


def chat(message, history):
    return ask(message)


demo = gr.ChatInterface(
    fn=chat,
    title="UmarTransit-1B",
    description="AI assistant for public transit systems and GTFS data. Ask about routes, stops, schedules, transfers, and GTFS concepts.",
    examples=[
        "What does route_type 3 mean in GTFS?",
        "What are the required files in a GTFS feed?",
        "How many routes does the Chicago Transit Authority operate?",
        "What is the difference between calendar.txt and calendar_dates.txt?",
        "Can GTFS times exceed 24:00:00?",
    ],
    theme="soft",
)

demo.launch()
