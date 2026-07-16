"""Check UmarTransit model, dataset, and derivative stats on HuggingFace.

Usage:
    python -m scripts.check_stats
"""

from huggingface_hub import HfApi

MODEL_ID = "umarfarookm/UmarTransit-1B"
DATASET_ID = "umarfarookm/UmarTransit-Instruct-3k"


def main() -> None:
    api = HfApi()

    # Model stats
    m = api.model_info(MODEL_ID)
    print("=" * 60)
    print(f"  MODEL: {MODEL_ID}")
    print("=" * 60)
    print(f"  Downloads:     {m.downloads:,}")
    print(f"  Likes:         {m.likes}")
    print(f"  Last modified: {m.last_modified}")
    print(f"  Tags:          {', '.join(m.tags or [])}")

    # Dataset stats
    d = api.dataset_info(DATASET_ID)
    print(f"\n{'=' * 60}")
    print(f"  DATASET: {DATASET_ID}")
    print("=" * 60)
    print(f"  Downloads:     {d.downloads:,}")
    print(f"  Likes:         {d.likes}")

    # Derivative models
    results = list(api.list_models(search="UmarTransit"))
    derivatives = [r for r in results if r.id != MODEL_ID]

    print(f"\n{'=' * 60}")
    print(f"  DERIVATIVE MODELS ({len(derivatives)} found)")
    print("=" * 60)
    if derivatives:
        for r in derivatives:
            print(f"  {r.id}")
            print(f"    Downloads: {r.downloads:,}  Likes: {r.likes}")
    else:
        print("  (none)")

    # GitHub stats
    try:
        import subprocess
        result = subprocess.run(
            ["gh", "api", "repos/umarfarookm/transit-foundation-model"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            import json
            repo = json.loads(result.stdout)
            print(f"\n{'=' * 60}")
            print(f"  GITHUB: umarfarookm/transit-foundation-model")
            print("=" * 60)
            print(f"  Stars:      {repo.get('stargazers_count', 0)}")
            print(f"  Forks:      {repo.get('forks_count', 0)}")
            print(f"  Watchers:   {repo.get('subscribers_count', 0)}")
            print(f"  Open issues: {repo.get('open_issues_count', 0)}")
    except Exception:
        pass

    print()


if __name__ == "__main__":
    main()
