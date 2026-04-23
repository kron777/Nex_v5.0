"""One-shot: download Kokoro-82M weights to HF cache.

Run this ONCE after install (or any time the model cache is cleared).
It temporarily disables HF offline mode for the scope of this script
only — your shell env is not modified.
"""
import os

# Override offline flags for this process only
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

from huggingface_hub import snapshot_download

REPO_ID = "hexgrad/Kokoro-82M"

print(f"Downloading {REPO_ID} to HF cache...")
print("(~350MB, one-time, resumable if interrupted)")

path = snapshot_download(repo_id=REPO_ID)
print(f"Downloaded to: {path}")
print("Done. Kokoro will now load from local cache on every boot.")
