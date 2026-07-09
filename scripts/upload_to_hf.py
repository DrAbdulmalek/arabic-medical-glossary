#!/usr/bin/env python3
"""Upload dataset to HuggingFace Hub using huggingface_hub API."""
import os, sys
from pathlib import Path
from huggingface_hub import HfApi, create_repo

REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
CLEANED_DIR = REPO_DIR / "cleaned"
HF_DATASET_ID = "DrAbdulmalek/arabic-bilingual-medical-glossary"

token = os.environ.get("HF_TOKEN")
if not token:
    print("ERROR: HF_TOKEN not set. Cannot upload.")
    print("Get a token from: https://huggingface.co/settings/tokens")
    sys.exit(1)

api = HfApi(token=token)

# Create dataset repo
print(f"Creating HF dataset: {HF_DATASET_ID}")
create_repo(
    repo_id=HF_DATASET_ID,
    token=token,
    repo_type="dataset",
    exist_ok=True,
    private=False,
)
print("  Repo ready.")

# Upload data files
uploads = [
    (DATA_DIR / "all_pairs.jsonl", "all_pairs.jsonl"),
    (DATA_DIR / "all_pairs.csv", "all_pairs.csv"),
    (DATA_DIR / "terms.csv", "terms.csv"),
    (DATA_DIR / "sentences.csv", "sentences.csv"),
    (DATA_DIR / "dataset_card.md", "README.md"),
]

for local, remote in uploads:
    if local.exists():
        print(f"  Uploading {remote}...")
        api.upload_file(
            path_or_fileobj=str(local),
            path_in_repo=remote,
            repo_id=HF_DATASET_ID,
            repo_type="dataset",
            token=token,
        )
        print(f"    OK")
    else:
        print(f"  SKIP {remote} (not found)")

# Upload cleaned files
for f in ["cleaned_glossary.csv", "terms.csv", "sentences.csv", "section_headers.csv"]:
    src = CLEANED_DIR / f
    if src.exists():
        print(f"  Uploading cleaned/{f}...")
        api.upload_file(
            path_or_fileobj=str(src),
            path_in_repo=f"cleaned/{f}",
            repo_id=HF_DATASET_ID,
            repo_type="dataset",
            token=token,
        )
        print(f"    OK")

print(f"\nDone! Dataset at: https://huggingface.co/datasets/{HF_DATASET_ID}")