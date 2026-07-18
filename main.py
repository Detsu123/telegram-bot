from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from collector import collect_news
from summarizer import (
    fallback_summary,
    summarize_with_gemini,
)
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

        return {
            str(item)
            for item in data
        }

    except (json.JSONDecodeError, OSError) as exc:
        print(
            f"[WARN] Could not read seen file: {exc}",
            flush=True,
        )

        return set()


def save_seen_ids(
    ids: set[str],
    keep_last: int = 2500,
) -> None:
    SEEN_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
        "[INFO] Starting AI Tech Telegram Bot...",
        flush=True,
    )

    bot_token = required_env(
        "TELEGRAM_BOT_TOKEN"
    )

    chat_id = required_env(
        "TELEGRAM_CHAT_ID"
    )

    gemini_api_key = required_env(
        "GEMINI_API_KEY"
    )

    gemini_model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.5-flash",
    ).strip()

    lookback_hours = int(
        os.getenv(
            "LOOKBACK_HOURS",
            "36",
        )
    )

    max_items_for_ai = int(
        os.getenv(
            "MAX_ITEMS_FOR_AI",
            "18",
        )
    )

    gemini_timeout = int(
        os.getenv(
            "GEMINI_TIMEOUT_SECONDS",
            "45",
        )
    )

    print(
        f"[INFO] Collecting news from the last "
        f"{lookback_hours} hours...",
        flush=True,
    )

    collect_start = time.time()

    collected = collect_news(
        lookback_hours=lookback_hours
    )

    collect_seconds = time.time() - collect_start

    print(
        f"[INFO] News collection completed in "
        f"{collect_seconds:.2f} seconds.",
        flush=True,
    )

    seen_ids = load_seen_ids()

    fresh_items = [
        item
        for item in collected
        if item.item_id not in seen_ids
    ]

    print(
        f"[INFO] Collected: {len(collected)}, "
        f"new: {len(fresh_items)}",
        flush=True,
    )

    if not fresh_items:
        print(
            "[INFO] No new items found. "
            "Nothing will be sent.",
            flush=True,
        )

        return 0

    selected = fresh_items[:max_items_for_ai]

    print(
        f"[INFO] Selected {len(selected)} items "
        f"for summarization.",
        flush=True,
    )

    print(
        f"[INFO] Starting Gemini summary. "
        f"Timeout: {gemini_timeout} seconds.",
        flush=True,
    )

    summary_start = time.time()

    try:
        digest = summarize_with_gemini(
            items=selected,
            api_key=gemini_api_key,
            model=gemini_model,
            timeout_seconds=gemini_timeout,
        )

        summary_seconds = (
            time.time() - summary_start
        )

        print(
            f"[INFO] Gemini summary completed in "
            f"{summary_seconds:.2f} seconds.",
            flush=True,
        )

    except Exception as exc:
        print(
            f"[WARN] Gemini summary failed: "
            f"{type(exc).__name__}: {exc}",
            flush=True,
        )

        print(
            "[INFO] Creating fallback summary...",
            flush=True,
        )

        digest = fallback_summary(selected)

    print(
        f"[INFO] Digest length: "
        f"{len(digest)} characters.",
        flush=True,
    )

    print(
        "[INFO] Sending message to Telegram...",
        flush=True,
    )

    telegram_start = time.time()

    send_telegram_message(
        bot_token=bot_token,
        chat_id=chat_id,
        text=digest,
    )

    telegram_seconds = (
        time.time() - telegram_start
    )

    print(
        f"[INFO] Telegram message sent in "
        f"{telegram_seconds:.2f} seconds.",
        flush=True,
    )

    seen_ids.update(
        item.item_id
        for item in selected
    )

    save_seen_ids(seen_ids)

    print(
        "[INFO] Duplicate-prevention state saved.",
        flush=True,
    )

    print(
        "[INFO] Digest sent successfully.",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except KeyboardInterrupt:
        print(
            "\n[INFO] Bot stopped by user.",
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