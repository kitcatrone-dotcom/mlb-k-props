"""
Pre-downloads model weights so the first analysis/separation run isn't slow
(and so the app can be used offline afterward).

Run from the backend venv:
    cd backend && source .venv/bin/activate && python ../scripts/download_models.py
"""
from __future__ import annotations

import sys


def download_demucs_weights() -> None:
    """Triggers torch.hub to fetch the htdemucs_ft checkpoint into the local
    torch cache (~/.cache/torch/hub/checkpoints)."""
    print("Fetching Demucs 'htdemucs_ft' weights (this can take a few minutes, ~laptop GPU/CPU size)...")
    try:
        from demucs.pretrained import get_model

        get_model("htdemucs_ft")
        print("  done.")
    except Exception as exc:  # pragma: no cover - network/environment dependent
        print(f"  WARNING: could not pre-fetch Demucs weights automatically ({exc}).")
        print("  They will be downloaded on first use instead.")


def main() -> int:
    download_demucs_weights()
    print("\nAll available models fetched. You're ready to run 'npm run dev'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
