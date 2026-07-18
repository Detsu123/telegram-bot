from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Iterable
from urllib.parse import urlencode

import feedparser
from dateutil import parser as date_parser

from sources import ARXIV_QUERIES, RSS_SOURCES


USER_AGENT = "TechNewsTelegramBot/1.0 (personal daily digest)"

HIGH_SIGNAL_KEYWORDS = {
    "new model": 18,
    "model release": 18,
    "introducing": 14,
    "launch": 10,
    "released": 10,
    "open source": 14,
    "open-source": 14,
    "weights": 12,
    "foundation model": 14,
    "language model": 12,
    "multimodal": 12,
    "reasoning": 8,
    "agent": 8,
    "robot": 8,
    "robotics": 10,
    "benchmark": 8,
    "state-of-the-art": 8,
    "sota": 8,
    "research": 5,
    "paper": 5,
    "dataset": 5,
    "text-to-video": 12,
    "text to video": 12,
    "vision-language": 12,
    "speech": 6,
    "inference": 6,
    "training": 5,
}

LOW_SIGNAL_KEYWORDS = {
    "webinar": -12,
    "event": -8,
    "hiring": -18,
    "job": -18,
    "podcast": -5,
    "sponsored": -20,
}


@dataclass
class NewsItem:
    item_id: str
    title: str
    url: str
    source: str
    published_at: str
    summary: str
    score: int

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _parse_entry_datetime(entry: dict) -> datetime | None:
    for key in ("published", "updated", "created"):
        raw = entry.get(key)
        if raw:
            try:
                dt = date_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue

    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        raw = entry.get(key)
        if raw:
            try:
                return datetime(*raw[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


def _canonical_id(title: str, url: str) -> str:
    normalized = f"{title.strip().lower()}|{url.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _score_item(title: str, summary: str, base_score: int) -> int:
    text = f"{title} {summary}".lower()
    score = base_score

    for keyword, points in HIGH_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += points

    for keyword, points in LOW_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += points

    # Titles are more important than descriptions.
    title_lower = title.lower()
    if any(word in title_lower for word in ("introducing", "new", "release", "model")):
        score += 8

    return score


def _entry_to_item(entry: dict, source_name: str, base_score: int) -> NewsItem | None:
    title = _clean_text(entry.get("title"))
    url = entry.get("link", "").strip()
    if not title or not url:
        return None

    published = _parse_entry_datetime(entry)
    if published is None:
        # Unknown dates are ignored to avoid resurfacing old articles.
        return None

    summary = _clean_text(entry.get("summary") or entry.get("description"))
    return NewsItem(
        item_id=_canonical_id(title, url),
        title=title,
        url=url,
        source=source_name,
        published_at=published.isoformat(),
        summary=summary[:1200],
        score=_score_item(title, summary, base_score),
    )


def _parse_feed(url: str):
    return feedparser.parse(
        url,
        request_headers={"User-Agent": USER_AGENT},
    )


def collect_rss(cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in RSS_SOURCES:
        try:
            feed = _parse_feed(source["url"])
            if getattr(feed, "bozo", False) and not feed.entries:
                print(f"[WARN] Feed failed: {source['name']} — {feed.bozo_exception}")
                continue

            for entry in feed.entries[:30]:
                item = _entry_to_item(
                    entry=entry,
                    source_name=source["name"],
                    base_score=int(source["base_score"]),
                )
                if item and datetime.fromisoformat(item.published_at) >= cutoff:
                    items.append(item)
        except Exception as exc:
            print(f"[WARN] Feed skipped: {source['name']} — {exc}")

    return items


def collect_arxiv(cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in ARXIV_QUERIES:
        params = {
            "search_query": source["query"],
            "start": 0,
            "max_results": 25,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"https://export.arxiv.org/api/query?{urlencode(params)}"

        try:
            feed = _parse_feed(url)
            if getattr(feed, "bozo", False) and not feed.entries:
                print(f"[WARN] arXiv query failed: {source['name']} — {feed.bozo_exception}")
                continue

            for entry in feed.entries:
                item = _entry_to_item(
                    entry=entry,
                    source_name=source["name"],
                    base_score=int(source["base_score"]),
                )
                if item and datetime.fromisoformat(item.published_at) >= cutoff:
                    items.append(item)
        except Exception as exc:
            print(f"[WARN] arXiv skipped: {source['name']} — {exc}")

    return items


def deduplicate(items: Iterable[NewsItem]) -> list[NewsItem]:
    best_by_title: dict[str, NewsItem] = {}

    for item in items:
        normalized_title = re.sub(r"[^a-z0-9]+", " ", item.title.lower()).strip()
        key = normalized_title[:180] or item.item_id
        existing = best_by_title.get(key)
        if existing is None or item.score > existing.score:
            best_by_title[key] = item

    return sorted(
        best_by_title.values(),
        key=lambda item: (item.score, item.published_at),
        reverse=True,
    )


def collect_news(lookback_hours: int) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    all_items = collect_rss(cutoff) + collect_arxiv(cutoff)
    return deduplicate(all_items)
