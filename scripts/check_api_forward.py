#!/usr/bin/env python
import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send real HDFS log lines to the FastAPI /forward route."
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000/forward",
        help="FastAPI /forward URL.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=ROOT / "data" / "HDFS.log",
        help="Path to raw HDFS.log.",
    )
    parser.add_argument(
        "--block-id",
        default="blk_7503483334202473044",
        help="Block id to extract from HDFS.log.",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=30,
        help="Maximum matching log lines to send.",
    )
    parser.add_argument(
        "--return-event-ids",
        action="store_true",
        help="Ask API to include parsed internal event ids.",
    )
    parser.add_argument(
        "--return-window-scores",
        action="store_true",
        help="Ask API to include per-window anomaly scores.",
    )
    return parser.parse_args()


def collect_log_lines(log_path: Path, block_id: str, max_lines: int) -> list[str]:
    lines = []
    with log_path.open("r", errors="ignore") as file:
        for line in file:
            if block_id in line:
                lines.append(line.rstrip("\n"))
            if len(lines) >= max_lines:
                break
    if not lines:
        raise RuntimeError(f"No log lines found for block_id={block_id}")
    return lines


def post_json(url: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw_error": body}
        return error.code, payload


def main() -> None:
    args = parse_args()
    lines = collect_log_lines(args.log_path, args.block_id, args.max_lines)
    payload = {
        "block_id": args.block_id,
        "log_lines": lines,
        "return_event_ids": args.return_event_ids,
        "return_window_scores": args.return_window_scores,
    }

    print("API URL:", args.api_url)
    print("Block id:", args.block_id)
    print("Log lines:", len(lines))

    status, result = post_json(args.api_url, payload)
    print("Status:", status)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
