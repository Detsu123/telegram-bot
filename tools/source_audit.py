"""Run source collection without Gemini or Telegram.

Usage:
    python -u tools/source_audit.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from collector import collect_news, select_candidates  # noqa: E402


def main() -> int:
    lookback_hours = int(
        os.getenv("LOOKBACK_HOURS", "48")
    )
    max_items = int(
        os.getenv("MAX_ITEMS_FOR_AI", "36")
    )

    items = collect_news(
        lookback_hours=lookback_hours
    )
    selected = select_candidates(
        items,
        max_total=max_items,
    )

    print("\n=== SOURCE AUDIT ===")
    print(f"Unique collected: {len(items)}")
    print(f"Selected candidates: {len(selected)}")

    tier_counts = Counter(
        item.trust_tier for item in items
    )
    print("\nTrust tiers:")
    for name, count in tier_counts.most_common():
        print(f"- {name}: {count}")

    source_counts = Counter(
        item.source for item in items
    )
    print("\nSources:")
    for name, count in source_counts.most_common():
        print(f"- {name}: {count}")

    print("\nSelected candidates:")
    for index, item in enumerate(selected, start=1):
        print(
            f"{index:02d}. [{item.trust_tier}] "
            f"{item.source} | {item.title}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
