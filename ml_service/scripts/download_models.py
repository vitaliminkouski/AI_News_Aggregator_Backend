#!/usr/bin/env python3
"""Utility script to pre-download Hugging Face models used by the ML microservice."""

import argparse
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download ML models required by the NewsAgent microservice.")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["summarization", "sentiment", "ner", "all"],
        default=["all"],
        help="Which models to download (default: all).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Optional custom cache directory for Hugging Face snapshots.",
    )
    parser.add_argument(
        "--local-dir",
        type=Path,
        default=None,
        help="Optional directory to place downloaded model weights (disabled symlinks).",
    )
    return parser.parse_args()


def resolve_targets(selected: Sequence[str]) -> Iterable[str]:
    if "all" in selected:
        return ("summarization", "sentiment", "ner")
    return selected


def download_model(
    label: str,
    model_id: str,
    revision: Optional[str],
    cache_dir: Optional[Path],
    local_dir: Optional[Path],
) -> None:
    print(f"[+] Downloading {label} model: {model_id} (revision={revision or 'latest'})")
    snapshot_download(
        repo_id=model_id,
        revision=revision,
        cache_dir=None if cache_dir is None else str(cache_dir),
        local_dir=None if local_dir is None else str(local_dir / label),
        local_dir_use_symlinks=False if local_dir is not None else True,
    )
    print(f"[✓] {label} model ready")


def main() -> None:
    args = parse_args()
    settings = get_settings()

    registry: Tuple[Tuple[str, str, Optional[str]], ...] = (
        ("summarization", settings.SUMMARIZATION_MODEL_NAME, settings.SUMMARIZATION_MODEL_REVISION),
        ("sentiment", settings.SENTIMENT_MODEL_NAME, settings.SENTIMENT_MODEL_REVISION),
        ("ner", settings.NER_MODEL_NAME, settings.NER_MODEL_REVISION),
    )

    wanted = set(resolve_targets(args.models))
    for label, model_id, revision in registry:
        if label not in wanted:
            continue
        download_model(label, model_id, revision, args.cache_dir, args.local_dir)

    print("Done.")


if __name__ == "__main__":
    main()

