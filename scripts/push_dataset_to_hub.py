"""Push UmarTransit-Instruct-3k dataset to Hugging Face Hub.

Usage:
    python -m scripts.push_dataset_to_hub

Requires:
    - huggingface-cli login (run once before first use)
    - datasets, huggingface_hub packages
"""

import json
import shutil
from pathlib import Path

from datasets import Dataset, DatasetDict
from huggingface_hub import HfApi

from scripts.config import SYNTHETIC_DIR, get_logger

log = get_logger(__name__)

REPO_ID = "umarfarookm/UmarTransit-Instruct-3k"
DATASET_CARD_PATH = SYNTHETIC_DIR / "DATASET_CARD.md"


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    log.info("Loading dataset splits...")
    train_data = load_jsonl(SYNTHETIC_DIR / "train.jsonl")
    test_data = load_jsonl(SYNTHETIC_DIR / "test.jsonl")
    log.info(f"  Train: {len(train_data)} pairs")
    log.info(f"  Test:  {len(test_data)} pairs")

    # Create HuggingFace Dataset objects
    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "test": Dataset.from_list(test_data),
    })
    log.info(f"Dataset created: {dataset}")

    # Push to Hub
    log.info(f"Pushing to {REPO_ID}...")
    dataset.push_to_hub(
        REPO_ID,
        private=False,
        commit_message="Upload UmarTransit-Instruct-3k dataset (3,306 transit Q&A pairs)",
    )
    log.info("Dataset uploaded successfully.")

    # Upload dataset card (README.md)
    if DATASET_CARD_PATH.exists():
        log.info("Uploading dataset card...")
        api = HfApi()
        api.upload_file(
            path_or_fileobj=str(DATASET_CARD_PATH),
            path_in_repo="README.md",
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message="Add dataset card",
        )
        log.info("Dataset card uploaded.")
    else:
        log.warning(f"Dataset card not found at {DATASET_CARD_PATH}")

    log.info(f"\nDone! View at: https://huggingface.co/datasets/{REPO_ID}")


if __name__ == "__main__":
    main()
