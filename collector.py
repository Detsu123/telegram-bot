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
from typing import Iterable, Optional
from urllib.parse import quote_plus, urlencode

import feedparser
import requests
from dateutil import parser as date_parser

from sources import (
    OFFICIAL_RSS_SOURCES,
    OFFICIAL_SITE_QUERIES,
    RESEARCH_SOURCES,
    TRUSTED_MEDIA_RSS_SOURCES,
)


USER_AGENT = "DetsuDailyGimme/3.0 (official-first personal AI digest)"
REQUEST_TIMEOUT = (10, 30)

STATUS_LABELS = {
    "official": "✅ Албан ёсны эх сурвалж",
    "research": "🧪 Анхдагч судалгааны эх сурвалж",
    "media": "📰 Хөндлөнгийн технологийн хэвлэл",
    "community": "💬 Community signal",
}

HIGH_SIGNAL_KEYWORDS = {
    "introducing": 14,
    "announce": 8,
    "launch": 10,
    "launched": 10,
    "release": 11,
    "released": 11,
    "new model": 18,
    "foundation model": 17,
    "language model": 14,
    "reasoning model": 15,
    "multimodal": 13,
    "agent": 8,
    "agentic": 9,
    "open source": 15,
    "open-source": 15,
    "open weight": 16,
    "open-weight": 16,
    "model weights": 16,
    "weights": 7,
    "research": 7,
    "technical report": 10,
    "paper": 7,
    "benchmark": 8,
    "dataset": 7,
    "api": 6,
    "sdk": 7,
    "developer": 4,
    "inference": 8,
    "training": 6,
    "fine-tuning": 7,
    "robot": 8,
    "robotics": 10,
    "humanoid": 11,
    "computer vision": 8,
    "vision-language": 12,
    "speech": 8,
    "text-to-speech": 11,
    "video generation": 11,
    "image generation": 9,
    "semiconductor": 9,
    "chip": 8,
    "gpu": 8,
    "processor": 7,
    "security vulnerability": 13,
    "zero-day": 17,
    "critical vulnerability": 16,
    "data breach": 12,
    "breakthrough": 14,
    "discovery": 9,
    "quantum": 9,
}

LOW_VALUE_PHRASES = {
    "opens office",
    "opening an office",
    "expands presence",
    "appoints",
    "named general manager",
    "joins the team",
    "hiring",
    "job opening",
    "webinar",
    "conference recap",
    "event recap",
    "customer story",
    "case study",
    "brand ambassador",
    "merch",
    "sponsorship",
    "partner program",
    "strategic partnership",
    "memorandum of understanding",
    "mou",
    "funding round",
    "raises $",
    "series a",
    "series b",
    "series c",
    "series d",
}

TECHNICAL_OVERRIDE_PHRASES = {
    "model",
    "research",
    "release",
    "open source",
    "open-source",
    "open weight",
    "open-weight",
    "api",
    "sdk",
    "benchmark",
    "dataset",
    "inference",
    "training",
    "security",
    "robot",
    "chip",
    "agent",
    "multimodal",
    "speech",
    "vision",
    "video",
    "audio",
    "developer",
}


@dataclass
class NewsItem:
    item_id: str
    title: str
    url: str
    source: str
    source_home: str
    category: str
    published_at: str
    summary: str
    score: int
    trust_tier: str
    status_label: str

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _strip_publisher_suffix(title: str) -> str:
    # Google News often appends " - Publisher" to a title.
    return re.sub(r"\s+[-–—]\s+[^-–—]{2,60}$", "", title).strip()


def _parse_entry_datetime(entry: dict) -> Optional[datetime]:
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
    normalized = f"{title.strip().lower()}|{url.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _is_low_value_story(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    has_low_value_phrase = any(phrase in text for phrase in LOW_VALUE_PHRASES)
    has_technical_override = any(
        phrase in text for phrase in TECHNICAL_OVERRIDE_PHRASES
    )
    return has_low_value_phrase and not has_technical_override


def _score_item(
    title: str,
    summary: str,
    base_score: int,
    trust_tier: str,
    extra_score: int = 0,
) -> int:
    text = f"{title} {summary}".lower()
    score = base_score + extra_score

    for keyword, points in HIGH_SIGNAL_KEYWORDS.items():
        if keyword in text:
            score += points

    if _is_low_value_story(title, summary):
        score -= 45

    if trust_tier == "official":
        score += 18
    elif trust_tier == "research":
        score += 12
    elif trust_tier == "media":
        score += 3
    elif trust_tier == "community":
        score -= 12

    title_lower = title.lower()
    if any(
        word in title_lower
        for word in (
            "introducing",
            "release",
            "launched",
            "breakthrough",
            "technical report",
        )
    ):
        score += 8

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


def _publisher_domain_matches(
    entry: dict,
    expected_domain: str,
    expected_name: str,
) -> bool:
    source = entry.get("source") or {}
    href = str(source.get("href") or "").lower()
    title = str(source.get("title") or "").lower()

    # If Google provides no publisher metadata, the site: query remains the
    # fallback restriction. If metadata exists, reject mismatched publishers.
    if not href and not title:
        return True

    expected = expected_domain.lower()
    if expected.startswith("www."):
        expected = expected[4:]

    normalized_href = href.replace("www.", "")
    if expected in normalized_href:
        return True

    compact_title = re.sub(r"[^a-z0-9]+", "", title)
    compact_name = re.sub(r"[^a-z0-9]+", "", expected_name.lower())

    return bool(compact_name) and compact_name in compact_title


def _entry_to_item(
    entry: dict,
    *,
    source_name: str,
    source_home: str,
    category: str,
    base_score: int,
    trust_tier: str,
    cutoff: datetime,
    allow_missing_date: bool = False,
    strip_publisher: bool = False,
) -> Optional[NewsItem]:
    title = _clean_text(entry.get("title"))
    if strip_publisher:
        title = _strip_publisher_suffix(title)

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

    # Official-first mode removes low-value corporate announcements before AI
    # summarization unless they contain a genuine technical signal.
    if trust_tier == "official" and _is_low_value_story(title, summary):
        return None

    return NewsItem(
        item_id=_canonical_id(title, url),
        title=title,
        url=url,
        source=source_name,
        source_home=source_home,
        category=category,
        published_at=published.isoformat(),
        summary=summary[:1500],
        score=_score_item(
            title=title,
            summary=summary,
            base_score=base_score,
            trust_tier=trust_tier,
        ),
        trust_tier=trust_tier,
        status_label=STATUS_LABELS[trust_tier],
    )


def _parse_feed(url: str):
    return feedparser.parse(
        url,
        request_headers={"User-Agent": USER_AGENT},
    )


def _collect_configured_feeds(
    sources: list[dict],
    *,
    cutoff: datetime,
    trust_tier: str,
    max_entries: int,
) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in sources:
        try:
            feed = _parse_feed(source["url"])
            if getattr(feed, "bozo", False) and not feed.entries:
                print(
                    f"[WARN] Feed skipped: {source['name']} — "
                    f"{feed.bozo_exception}",
                    flush=True,
                )
                continue

            before = len(items)
            for rank, entry in enumerate(feed.entries[:max_entries]):
                item = _entry_to_item(
                    entry,
                    source_name=source["name"],
                    source_home=source["home"],
                    category=source["category"],
                    base_score=int(source["base_score"]),
                    trust_tier=trust_tier,
                    cutoff=cutoff,
                    allow_missing_date=rank < 6,
                )
                if item:
                    items.append(item)

            added = len(items) - before
            if added:
                print(
                    f"[INFO] {STATUS_LABELS[trust_tier]} "
                    f"{source['name']}: {added}",
                    flush=True,
                )

        except Exception as exc:
            print(
                f"[WARN] Feed skipped: {source['name']} — {exc}",
                flush=True,
            )

    return items


def collect_official_rss(cutoff: datetime) -> list[NewsItem]:
    return _collect_configured_feeds(
        OFFICIAL_RSS_SOURCES,
        cutoff=cutoff,
        trust_tier="official",
        max_entries=35,
    )


def collect_official_site_queries(cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in OFFICIAL_SITE_QUERIES:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(source['query'])}"
            "&hl=en-US&gl=US&ceid=US:en"
        )

        try:
            feed = _parse_feed(url)
            if getattr(feed, "bozo", False) and not feed.entries:
                print(
                    f"[WARN] Official site query skipped: {source['name']}",
                    flush=True,
                )
                continue

            before = len(items)
            for entry in feed.entries[:25]:
                if not _publisher_domain_matches(
                    entry,
                    source["domain"],
                    source["name"],
                ):
                    continue

                item = _entry_to_item(
                    entry,
                    source_name=source["name"],
                    source_home=source["home"],
                    category=source["category"],
                    base_score=int(source["base_score"]),
                    trust_tier="official",
                    cutoff=cutoff,
                    strip_publisher=True,
                )
                if item:
                    items.append(item)

            added = len(items) - before
            if added:
                print(
                    f"[INFO] ✅ Official site {source['name']}: {added}",
                    flush=True,
                )

        except Exception as exc:
            print(
                f"[WARN] Official site query skipped: "
                f"{source['name']} — {exc}",
                flush=True,
            )

    return items


def collect_research(cutoff: datetime) -> list[NewsItem]:
    items: list[NewsItem] = []

    for source in RESEARCH_SOURCES:
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
                    entry,
                    source_name=source["name"],
                    source_home="https://arxiv.org/",
                    category=source["category"],
                    base_score=int(source["base_score"]),
                    trust_tier="research",
                    cutoff=cutoff,
                )
                if item:
                    items.append(item)
        except Exception as exc:
            print(
                f"[WARN] Research feed skipped: "
                f"{source['name']} — {exc}",
                flush=True,
            )

    if items:
        print(f"[INFO] 🧪 Research total: {len(items)}", flush=True)

    return items


def collect_trusted_media(cutoff: datetime) -> list[NewsItem]:
    return _collect_configured_feeds(
        TRUSTED_MEDIA_RSS_SOURCES,
        cutoff=cutoff,
        trust_tier="media",
        max_entries=35,
    )


def _fetch_hn_item(item_id: int) -> Optional[dict]:
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
        story_ids = response.json()[:40]
    except Exception as exc:
        print(f"[WARN] Hacker News skipped — {exc}", flush=True)
        return []

    raw_items: list[dict] = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(_fetch_hn_item, item_id)
            for item_id in story_ids
        ]
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
        points = int(raw.get("score", 0))
        comments = int(raw.get("descendants", 0))
        summary = f"Hacker News points: {points}; comments: {comments}"

        items.append(
            NewsItem(
                item_id=_canonical_id(title, url),
                title=title,
                url=url,
                source="Hacker News",
                source_home="https://news.ycombinator.com/",
                category="Community Discovery",
                published_at=published.isoformat(),
                summary=summary,
                score=_score_item(
                    title=title,
                    summary=summary,
                    base_score=18,
                    trust_tier="community",
                    extra_score=min(points // 20, 10)
                    + min(comments // 30, 5),
                ),
                trust_tier="community",
                status_label=STATUS_LABELS["community"],
            )
        )

    print(f"[INFO] 💬 Hacker News: {len(items)}", flush=True)
    return items


def collect_github_repositories(
    cutoff: datetime,
) -> list[NewsItem]:
    search_queries = [
        (
            f"created:>={cutoff.strftime('%Y-%m-%d')} "
            "stars:>=40 topic:artificial-intelligence"
        ),
        (
            f"created:>={cutoff.strftime('%Y-%m-%d')} "
            "stars:>=40 topic:llm"
        ),
        (
            f"created:>={cutoff.strftime('%Y-%m-%d')} "
            "stars:>=40 topic:generative-ai"
        ),
    ]

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_API_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    repositories_by_url: dict = {}

    for query in search_queries:
        try:
            response = requests.get(
                "https://api.github.com/search/repositories",
                params={
                    "q": query,
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 10,
                },
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            for repository in response.json().get("items", []):
                url = str(repository.get("html_url") or "")
                if url:
                    repositories_by_url[url] = repository

        except Exception as exc:
            print(
                f"[WARN] GitHub discovery query skipped — {exc}",
                flush=True,
            )

    repositories = sorted(
        repositories_by_url.values(),
        key=lambda repository: int(
            repository.get("stargazers_count", 0)
        ),
        reverse=True,
    )[:15]

    items: list[NewsItem] = []

    for repo in repositories:
        url = str(repo.get("html_url") or "")
        if not url:
            continue

        full_name = str(
            repo.get("full_name") or "New repository"
        )
        title = (
            f"{full_name} — шинэ open-source AI төсөл"
        )
        description = _clean_text(
            repo.get("description")
        )
        stars = int(
            repo.get("stargazers_count", 0)
        )
        language = repo.get("language") or "Unknown"
        summary = (
            f"{description} | Language: {language} | "
            f"Stars: {stars}"
        )
        published = date_parser.parse(
            repo["created_at"]
        ).astimezone(timezone.utc)

        items.append(
            NewsItem(
                item_id=_canonical_id(title, url),
                title=title,
                url=url,
                source="GitHub New AI Repositories",
                source_home="https://github.com/",
                category="Open Source Discovery",
                published_at=published.isoformat(),
                summary=summary,
                score=_score_item(
                    title=title,
                    summary=summary,
                    base_score=22,
                    trust_tier="community",
                    extra_score=min(stars // 15, 12),
                ),
                trust_tier="community",
                status_label=STATUS_LABELS["community"],
            )
        )

    print(
        f"[INFO] 💬 GitHub AI repository discovery: "
        f"{len(items)}",
        flush=True,
    )
    return items


def _normalized_title(title: str) -> str:
    title = _strip_publisher_suffix(title)
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _trust_rank(item: NewsItem) -> int:
    return {
        "official": 4,
        "research": 3,
        "media": 2,
        "community": 1,
    }.get(item.trust_tier, 0)


def deduplicate(items: Iterable[NewsItem]) -> list[NewsItem]:
    ordered = sorted(
        items,
        key=lambda item: (
            _trust_rank(item),
            item.score,
            item.published_at,
        ),
        reverse=True,
    )

    kept: list[NewsItem] = []
    normalized_kept: list[str] = []
    seen_urls: set[str] = set()

    for item in ordered:
        if item.url in seen_urls:
            continue

        normalized = _normalized_title(item.title)
        duplicate_index: Optional[int] = None

        for index, existing in enumerate(normalized_kept):
            if normalized == existing:
                duplicate_index = index
                break

            if len(normalized) > 25 and len(existing) > 25:
                similarity = SequenceMatcher(
                    None,
                    normalized,
                    existing,
                ).ratio()
                if similarity >= 0.88:
                    duplicate_index = index
                    break

        if duplicate_index is not None:
            current = kept[duplicate_index]
            # Replace secondary/community coverage with the first-party version.
            if _trust_rank(item) > _trust_rank(current):
                kept[duplicate_index] = item
                normalized_kept[duplicate_index] = normalized
            continue

        kept.append(item)
        normalized_kept.append(normalized)
        seen_urls.add(item.url)

    return sorted(
        kept,
        key=lambda item: (
            _trust_rank(item),
            item.score,
            item.published_at,
        ),
        reverse=True,
    )


def _append_diverse(
    destination: list[NewsItem],
    pool: list[NewsItem],
    *,
    limit: int,
    max_per_source: int,
    max_per_category: int,
) -> None:
    selected_ids = {item.item_id for item in destination}
    source_counts = Counter(item.source for item in destination)
    category_counts = Counter(item.category for item in destination)

    for item in pool:
        if len(destination) >= limit:
            return
        if item.item_id in selected_ids:
            continue
        if source_counts[item.source] >= max_per_source:
            continue
        if category_counts[item.category] >= max_per_category:
            continue

        destination.append(item)
        selected_ids.add(item.item_id)
        source_counts[item.source] += 1
        category_counts[item.category] += 1


def select_candidates(
    items: list[NewsItem],
    max_total: int = 36,
) -> list[NewsItem]:
    official = [item for item in items if item.trust_tier == "official"]
    research = [item for item in items if item.trust_tier == "research"]
    media = [item for item in items if item.trust_tier == "media"]
    community = [item for item in items if item.trust_tier == "community"]

    selected: list[NewsItem] = []

    # Target mix when enough content exists:
    # 22 official + 7 research + 5 independent media + 2 community signals.
    _append_diverse(
        selected,
        official,
        limit=min(max_total, 22),
        max_per_source=4,
        max_per_category=8,
    )
    _append_diverse(
        selected,
        research,
        limit=min(max_total, len(selected) + 7),
        max_per_source=3,
        max_per_category=8,
    )
    _append_diverse(
        selected,
        media,
        limit=min(max_total, len(selected) + 5),
        max_per_source=3,
        max_per_category=8,
    )
    _append_diverse(
        selected,
        community,
        limit=min(max_total, len(selected) + 2),
        max_per_source=2,
        max_per_category=8,
    )

    # Fill unused capacity by trust and score.
    if len(selected) < max_total:
        selected_ids = {item.item_id for item in selected}
        for item in items:
            if item.item_id in selected_ids:
                continue
            selected.append(item)
            selected_ids.add(item.item_id)
            if len(selected) >= max_total:
                break

    return selected


def collect_news(lookback_hours: int) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=lookback_hours
    )

    all_items: list[NewsItem] = []
    all_items.extend(collect_official_rss(cutoff))
    all_items.extend(collect_official_site_queries(cutoff))
    all_items.extend(collect_research(cutoff))
    all_items.extend(collect_trusted_media(cutoff))
    all_items.extend(collect_hacker_news(cutoff))
    all_items.extend(collect_github_repositories(cutoff))

    unique_items = deduplicate(all_items)

    tier_counts = Counter(item.trust_tier for item in unique_items)
    print(
        f"[INFO] Raw: {len(all_items)}, deduplicated: "
        f"{len(unique_items)}",
        flush=True,
    )
    print(
        "[INFO] Trust tiers: "
        + ", ".join(
            f"{tier}={count}"
            for tier, count in tier_counts.most_common()
        ),
        flush=True,
    )

    return unique_items
