from __future__ import annotations

import hashlib
import html
import os
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Iterable
from urllib.parse import quote_plus, urlencode

import feedparser
import requests
from dateutil import parser as date_parser

from sources import ARXIV_QUERIES, GOOGLE_NEWS_QUERIES, RSS_SOURCES


USER_AGENT = "DetsuDailyGimme/2.0 (personal technology digest)"
REQUEST_TIMEOUT = (10, 25)

HIGH_SIGNAL_KEYWORDS = {
    "introducing": 12,
    "launches": 9,
    "launched": 9,
    "release": 9,
    "released": 9,
    "new model": 15,
    "foundation model": 15,
    "language model": 12,
    "multimodal": 11,
    "reasoning": 7,
    "open source": 12,
    "open-source": 12,
    "model weights": 14,
    "weights": 7,
    "breakthrough": 14,
    "discovery": 9,
    "research": 5,
    "robot": 7,
    "robotics": 9,
    "humanoid": 10,
    "semiconductor": 8,
    "chip": 7,
    "gpu": 7,
    "processor": 6,
    "security vulnerability": 12,
    "zero-day": 15,
    "critical vulnerability": 15,
    "data breach": 11,
    "spacecraft": 7,
    "satellite": 6,
    "rocket": 6,
    "quantum": 8,
    "battery": 6,
    "fusion": 9,
    "api": 4,
    "developer": 4,
    "benchmark": 7,
    "dataset": 5,
}

LOW_SIGNAL_KEYWORDS = {
    "webinar": -15,
    "podcast": -7,
    "sponsored": -25,
    "advertisement": -25,
    "coupon": -25,
    "deal": -9,
    "review": -4,
    "rumor": -8,
    "opinion": -5,
    "hiring": -18,
    "job opening": -18,
}


@dataclass
class NewsItem:
    item_id: str
    title: str
    url: str
    source: str
    category: str
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
                pass

    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        raw = entry.get(key)
        if raw:
            try:
                return datetime(*raw[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass

    return None


def _canonical_id(title: str, url: str) -> str:
    value = f"{title.strip().lower()}|{url.strip()}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _score_item(
    title: str,
    summary: str,
    base_score: int,
    extra_score: int = 0,
) -> int:
    text = f"{title} {summary}".lower()
    score = base_score + extra_score

    for keyword, points in HIGH_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += points

    for keyword, points in LOW_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += points

    if any(
        word in title.lower()
        for word in ("introducing", "launch", "release", "breakthrough")
    ):
        score += 7

    return score


def _entry_url(entry: dict) -> str:
    link = str(entry.get("link") or "").strip()
    if link:
        return link

    guid = str(entry.get("id") or entry.get("guid") or "").strip()
    if guid.startswith("http"):
        return guid

    for item in entry.get("links") or []:
        href = str(item.get("href") or "").strip()
        if href:
            return href

    return ""


def _entry_to_item(
    entry: dict,
    source_name: str,
    category: str,
    base_score: int,
    cutoff: datetime,
    allow_missing_date: bool = False,
) -> NewsItem | None:
    title = _clean_text(entry.get("title"))
    url = _entry_url(entry)
    if not title or not url:
        return None

    published = _parse_entry_datetime(entry)
    if published is None:
        if not allow_missing_date:
            return None
        published = datetime.now(timezone.utc)

    if published < cutoff:
        return None

    summary = _clean_text(entry.get("summary") or entry.get("description"))
    return NewsItem(
        item_id=_canonical_id(title, url),
        title=title,
        url=url,
        source=source_name,
        category=category,
        published_at=published.isoformat(),
        summary=summary[:1400],
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
                print(
                    f"[WARN] RSS skipped: {source['name']} — {feed.bozo_exception}",
                    flush=True,
                )
                continue

            before = len(items)
            for rank, entry in enumerate(feed.entries[:35]):
                item = _entry_to_item(
                    entry=entry,
                    source_name=source["name"],
                    category=source["category"],
                    base_score=int(source["base_score"]),
                    cutoff=cutoff,
                    allow_missing_date=rank < 8,
                )
                if item:
                    items.append(item)

            added = len(items) - before
            if added:
                print(f"[INFO] RSS {source['name']}: {added}", flush=True)

        except Exception as exc:
            print(f"[WARN] RSS skipped: {source['name']} — {exc}", flush=True)

    return items


def collect_google_news(cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in GOOGLE_NEWS_QUERIES:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(source['query'])}&hl=en-US&gl=US&ceid=US:en"
        )

        try:
            feed = _parse_feed(url)
            if getattr(feed, "bozo", False) and not feed.entries:
                continue

            before = len(items)
            for entry in feed.entries[:30]:
                item = _entry_to_item(
                    entry=entry,
                    source_name=f"Google News: {source['name']}",
                    category=source["category"],
                    base_score=int(source["base_score"]),
                    cutoff=cutoff,
                )
                if item:
                    items.append(item)

            added = len(items) - before
            if added:
                print(
                    f"[INFO] Google News {source['name']}: {added}",
                    flush=True,
                )

        except Exception as exc:
            print(
                f"[WARN] Google News skipped: {source['name']} — {exc}",
                flush=True,
            )

    return items


def collect_arxiv(cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in ARXIV_QUERIES:
        params = {
            "search_query": source["query"],
            "start": 0,
            "max_results": 18,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"https://export.arxiv.org/api/query?{urlencode(params)}"

        try:
            feed = _parse_feed(url)
            for entry in feed.entries:
                item = _entry_to_item(
                    entry=entry,
                    source_name=source["name"],
                    category=source["category"],
                    base_score=int(source["base_score"]),
                    cutoff=cutoff,
                )
                if item:
                    items.append(item)
        except Exception as exc:
            print(f"[WARN] arXiv skipped: {source['name']} — {exc}", flush=True)

    if items:
        print(f"[INFO] arXiv total: {len(items)}", flush=True)
    return items


def _fetch_hn_item(item_id: int) -> dict | None:
    try:
        response = requests.get(
            f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def collect_hacker_news(cutoff: datetime) -> list[NewsItem]:
    try:
        response = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        story_ids = response.json()[:45]
    except Exception as exc:
        print(f"[WARN] Hacker News skipped — {exc}", flush=True)
        return []

    raw_items: list[dict] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_hn_item, item_id) for item_id in story_ids]
        for future in as_completed(futures):
            item = future.result()
            if item:
                raw_items.append(item)

    items: list[NewsItem] = []
    for raw in raw_items:
        if raw.get("type") != "story" or not raw.get("title"):
            continue

        published = datetime.fromtimestamp(
            int(raw.get("time", 0)),
            tz=timezone.utc,
        )
        if published < cutoff:
            continue

        title = _clean_text(raw["title"])
        url = str(
            raw.get("url")
            or f"https://news.ycombinator.com/item?id={raw['id']}"
        )
        hn_score = min(int(raw.get("score", 0)) // 12, 18)
        comments_score = min(int(raw.get("descendants", 0)) // 20, 8)
        summary = (
            f"Hacker News score: {raw.get('score', 0)}; "
            f"comments: {raw.get('descendants', 0)}"
        )

        items.append(
            NewsItem(
                item_id=_canonical_id(title, url),
                title=title,
                url=url,
                source="Hacker News",
                category="General Technology",
                published_at=published.isoformat(),
                summary=summary,
                score=_score_item(
                    title,
                    summary,
                    23,
                    hn_score + comments_score,
                ),
            )
        )

    print(f"[INFO] Hacker News: {len(items)}", flush=True)
    return items


def collect_github_repositories(cutoff: datetime) -> list[NewsItem]:
    params = {
        "q": f"created:>={cutoff.strftime('%Y-%m-%d')} stars:>=20",
        "sort": "stars",
        "order": "desc",
        "per_page": 20,
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            "https://api.github.com/search/repositories",
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        repositories = response.json().get("items", [])
    except Exception as exc:
        print(f"[WARN] GitHub repositories skipped — {exc}", flush=True)
        return []

    items: list[NewsItem] = []
    for repo in repositories:
        title = f"{repo.get('full_name', 'New repository')} — new open-source project"
        url = str(repo.get("html_url") or "")
        if not url:
            continue

        description = _clean_text(repo.get("description"))
        stars = int(repo.get("stargazers_count", 0))
        language = repo.get("language") or "Unknown"
        summary = f"{description} | Language: {language} | Stars: {stars}"
        published = date_parser.parse(repo["created_at"]).astimezone(timezone.utc)

        items.append(
            NewsItem(
                item_id=_canonical_id(title, url),
                title=title,
                url=url,
                source="GitHub New Repositories",
                category="Software & Open Source",
                published_at=published.isoformat(),
                summary=summary,
                score=_score_item(
                    title,
                    summary,
                    24,
                    min(stars // 10, 20),
                ),
            )
        )

    print(f"[INFO] GitHub new repositories: {len(items)}", flush=True)
    return items


def _normalized_title(title: str) -> str:
    title = re.sub(r"\s+[-–—]\s+[^-–—]{2,45}$", "", title)
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def deduplicate(items: Iterable[NewsItem]) -> list[NewsItem]:
    ordered = sorted(
        items,
        key=lambda item: (item.score, item.published_at),
        reverse=True,
    )
    kept: list[NewsItem] = []
    normalized_kept: list[str] = []
    seen_urls: set[str] = set()

    for item in ordered:
        if item.url in seen_urls:
            continue

        normalized = _normalized_title(item.title)
        duplicate = False

        for existing in normalized_kept:
            if normalized == existing:
                duplicate = True
                break
            if len(normalized) > 25 and len(existing) > 25:
                if SequenceMatcher(None, normalized, existing).ratio() >= 0.90:
                    duplicate = True
                    break

        if duplicate:
            continue

        kept.append(item)
        normalized_kept.append(normalized)
        seen_urls.add(item.url)

    return kept


def select_candidates(
    items: list[NewsItem],
    max_total: int = 32,
    max_per_category: int = 6,
    max_per_source: int = 4,
) -> list[NewsItem]:
    category_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    selected: list[NewsItem] = []

    ordered = sorted(
        items,
        key=lambda item: (item.score, item.published_at),
        reverse=True,
    )

    for item in ordered:
        if category_counts[item.category] >= max_per_category:
            continue
        if source_counts[item.source] >= max_per_source:
            continue

        selected.append(item)
        category_counts[item.category] += 1
        source_counts[item.source] += 1

        if len(selected) >= max_total:
            return selected

    selected_ids = {item.item_id for item in selected}
    for item in ordered:
        if item.item_id in selected_ids:
            continue
        selected.append(item)
        if len(selected) >= max_total:
            break

    return selected


def collect_news(lookback_hours: int) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    all_items: list[NewsItem] = []
    all_items.extend(collect_rss(cutoff))
    all_items.extend(collect_google_news(cutoff))
    all_items.extend(collect_hacker_news(cutoff))
    all_items.extend(collect_github_repositories(cutoff))
    all_items.extend(collect_arxiv(cutoff))

    unique_items = deduplicate(all_items)
    print(
        f"[INFO] Raw items: {len(all_items)}, "
        f"after deduplication: {len(unique_items)}",
        flush=True,
    )
    return unique_items
