from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from collector import collect_news, select_candidates
from summarizer import fallback_summary, summarize_with_gemini
from telegram_sender import send_telegram_message


SEEN_PATH = Path("data/seen_items.json")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}"
        )
    return value


def load_seen_ids() -> set[str]:
    if not SEEN_PATH.exists():
        return set()

    try:
        data = json.loads(
            SEEN_PATH.read_text(encoding="utf-8")
        )
        return {str(item) for item in data}
    except (json.JSONDecodeError, OSError) as exc:
        print(
            f"[WARN] Could not read seen file: {exc}",
            flush=True,
        )
        return set()


def save_seen_ids(ids: set[str], keep_last: int = 10000) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    trimmed = sorted(ids)[-keep_last:]
    SEEN_PATH.write_text(
        json.dumps(
            trimmed,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    print(
        "[INFO] Starting AI & Technology Digest V2...",
        flush=True,
    )

    bot_token = required_env("TELEGRAM_BOT_TOKEN")
    chat_id = required_env("TELEGRAM_CHAT_ID")
    gemini_api_key = required_env("GEMINI_API_KEY")

    gemini_model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.1-flash-lite",
    ).strip()
    lookback_hours = int(
        os.getenv("LOOKBACK_HOURS", "42")
    )
    max_items_for_ai = int(
        os.getenv("MAX_ITEMS_FOR_AI", "32")
    )
    max_summary_items = int(
        os.getenv("MAX_SUMMARY_ITEMS", "15")
    )
    gemini_timeout = int(
        os.getenv("GEMINI_TIMEOUT_SECONDS", "120")
    )

    started = time.time()
    collected = collect_news(
        lookback_hours=lookback_hours
    )
    print(
        f"[INFO] Collection completed in "
        f"{time.time() - started:.2f} seconds.",
        flush=True,
    )

    seen_ids = load_seen_ids()
    fresh_items = [
        item
        for item in collected
        if item.item_id not in seen_ids
    ]

    print(
        f"[INFO] Collected unique: {len(collected)}, "
        f"unseen: {len(fresh_items)}",
        flush=True,
    )

    if not fresh_items:
        print(
            "[INFO] No new items. Nothing sent.",
            flush=True,
        )
        return 0

    category_counts = Counter(
        item.category for item in fresh_items
    )
    print(
        "[INFO] Fresh categories: "
        + ", ".join(
            f"{name}={count}"
            for name, count in category_counts.most_common()
        ),
        flush=True,
    )

    candidates = select_candidates(
        fresh_items,
        max_total=max_items_for_ai,
        max_per_category=6,
        max_per_source=4,
    )
    print(
        f"[INFO] Selected {len(candidates)} "
        f"candidates for Gemini.",
        flush=True,
    )

    try:
        digest = summarize_with_gemini(
            items=candidates,
            api_key=gemini_api_key,
            model=gemini_model,
            timeout_seconds=gemini_timeout,
            max_summary_items=max_summary_items,
        )
        print(
            "[INFO] AI summary completed.",
            flush=True,
        )
    except Exception as exc:
        print(
            f"[WARN] AI summary failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )
        digest = fallback_summary(
            candidates,
            max_summary_items=max_summary_items,
        )

    print(
        f"[INFO] Digest length: "
        f"{len(digest)} characters.",
        flush=True,
    )
    print(
        "[INFO] Sending digest to Telegram...",
        flush=True,
    )

    send_telegram_message(
        bot_token=bot_token,
        chat_id=chat_id,
        text=digest,
    )

    seen_ids.update(
        item.item_id for item in fresh_items
    )
    save_seen_ids(seen_ids)

    print(
        "[INFO] Digest sent and state saved successfully.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(
            "\n[INFO] Stopped by user.",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(130)
    except Exception as exc:
        print(
            f"[ERROR] {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1)
