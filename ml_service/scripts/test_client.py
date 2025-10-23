#!/usr/bin/env python3
import argparse
import json
from typing import Any, Dict

import requests


def build_payload(mode: str, text: str, min_tokens: int | None, max_tokens: int | None) -> Dict[str, Any]:
    base = {"text": text}
    if mode in {"summarize", "analyze"}:
        if min_tokens is not None:
            base["min_tokens"] = min_tokens
        if max_tokens is not None:
            base["max_tokens"] = max_tokens
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick client for NewsAgent ML microservice.")
    parser.add_argument("--host", default="http://127.0.0.1", help="Base host of the service")
    parser.add_argument("--port", type=int, default=8100, help="Service port")
    parser.add_argument(
        "--mode",
        choices=["summarize", "sentiment", "ner", "analyze"],
        default="analyze",
        help="Endpoint to call",
    )
    parser.add_argument("--text", required=True, help="Text to process")
    parser.add_argument("--min-tokens", type=int, default=None, help="Min tokens for summarization")
    parser.add_argument("--max-tokens", type=int, default=None, help="Max tokens for summarization")
    args = parser.parse_args()

    url = f"{args.host}:{args.port}"
    endpoint_map = {
        "summarize": "/v1/summarize",
        "sentiment": "/v1/sentiment",
        "ner": "/v1/ner",
        "analyze": "/v1/analyze",
    }
    payload = build_payload(args.mode, args.text, args.min_tokens, args.max_tokens)

    response = requests.post(f"{url}{endpoint_map[args.mode]}", json=payload, timeout=60)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        print(f"Request failed ({response.status_code}): {exc}")
        print(response.text)
        raise SystemExit(1)

    print(json.dumps(response.json(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

