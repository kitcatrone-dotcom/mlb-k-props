# Models

This project doesn't vendor model weights in the repo — they're fetched into
your local cache the first time you run `scripts/download_models.py` (or the
first time separation runs, if you skip that step).

| Model | Source | Cached at | Size |
|---|---|---|---|
| `htdemucs_ft` (Demucs v4, fine-tuned 4-stem) | `demucs` PyPI package, weights pulled from Meta's public model hub via `torch.hub` | `~/.cache/torch/hub/checkpoints/` | ~330MB |

No API keys are required — everything runs locally, offline after the first
download, on CPU or GPU (CUDA/MPS auto-detected by PyTorch).

If you want to experiment with the optional Essentia genre/mood classifier
mentioned in `ARCHITECTURE.md`, see the note in
`backend/app/audio/analysis/energy.py` — it documents the pretrained model ID
and where to plug it in without changing the rest of the pipeline.
