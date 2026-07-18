from __future__ import annotations

import time
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from collector import NewsItem


ULAANBAATAR = ZoneInfo("Asia/Ulaanbaatar")


def _build_prompt(
    items: list[NewsItem],
    max_summary_items: int,
) -> str:
    source_text = "\n\n".join(
        (
            f"[{index}]\n"
            f"TITLE: {item.title}\n"
            f"CATEGORY: {item.category}\n"
            f"SOURCE: {item.source}\n"
            f"SOURCE_HOME: {item.source_home}\n"
            f"TRUST_TIER: {item.trust_tier}\n"
            f"STATUS: {item.status_label}\n"
            f"PUBLISHED: {item.published_at}\n"
            f"IMPORTANCE_SCORE: {item.score}\n"
            f"DESCRIPTION: {item.summary[:650]}\n"
            f"ARTICLE_URL: {item.url}"
        )
        for index, item in enumerate(items, start=1)
    )

    today = datetime.now(ULAANBAATAR).strftime("%Y-%m-%d")
    official_available = sum(
        1 for item in items if item.trust_tier == "official"
    )

    return f"""
Чи AI болон технологийн мэдээний Монгол хэлний редактор.
Энэ digest-ийн гол зарчим нь OFFICIAL-FIRST.

Доорх {len(items)} нэр дэвшигчээс хамгийн ихдээ
{max_summary_items} үнэхээр хэрэгтэй мэдээллийг сонго.
Нэр дэвшигчдийн {official_available} нь албан ёсны эх сурвалжтай.

ЭХ СУРВАЛЖИЙН ЭРЭМБЭ:
1. official — компанийн/лабораторийн өөрийн зарлал
2. research — arXiv зэрэг анхдагч судалгааны эх сурвалж
3. media — хөндлөнгийн нэр хүндтэй технологийн хэвлэл
4. community — зөвхөн шинэ сэдэв илрүүлэх signal; баталгаа биш

СОНГОЛТЫН ДҮРЭМ:
1. Албан ёсны шинэ model, product, API, SDK, research, open-source,
   model weights, benchmark, infrastructure release-ийг хамгийн түрүүнд сонго.
2. Албан ёсны мэдээлэл хангалттай байвал дор хаяж 8-ыг official
   эх сурвалжаас сонго.
3. Office нээсэн, хүн томилсон, funding, partnership, customer story,
   webinar, merch зэрэг технологийн бодит шинэчлэлгүй мэдээллийг бүү сонго.
4. Нэг үйл явдлын official болон media хувилбар байвал official-ийг үндсэн
   эх сурвалж болго. Media эх сурвалжийг зөвхөн хөндлөнгийн контекст болгон
   ашигла.
5. Community мэдээллийг official/research/media баталгаагүй бол
   "баталгаажаагүй community signal" гэж тодорхой тэмдэглэ эсвэл хас.
6. Компанийн өөрийн benchmark, "хамгийн сайн", "хамгийн хурдан" гэх
   claims-ийг баримт мэт баталгаажуулж болохгүй. "Компанийн өөрийн
   мэдээллээр" гэж тодруул.
7. Эх мэдээлэлд model weights, API, код, лиценз, benchmark байгаа эсэх нь
   тодорхой биш бол зохиож болохгүй.
8. Давхардсан үйл явдлыг нэг мэдээ болго.
9. Clickbait гарчгийг тайван, бодит гарчиг болго.
10. Монгол хэлээр ойлгомжтой, товч, мэргэжлийн бич.
11. Telegram Markdown ашиглахгүй. Энгийн текст хэрэглэ.
12. Нийт хариу 7600 тэмдэгтээс хэтрэхгүй.

МЭДЭЭ БҮРИЙН ХЭЛБЭР:
№. Гарчиг
Статус: өгөгдсөн STATUS-г яг хэрэглэ
Юу болсон: 1–2 өгүүлбэр
Яагаад чухал: 1 өгүүлбэр
Бодит хэрэглээ: 1 өгүүлбэр
Баталгааны тайлбар: official бол компанийн өөрийн claim эсэхийг ялга
Эх сурвалж: ARTICLE_URL

ГАРАЛТЫН БҮТЭЦ:
🤖 AI & Tech Official Daily — {today}

🔥 Өдрийн онцлох 3
...

🏢 Албан ёсны шинэчлэлтүүд
...

🧪 Судалгаа ба open-source
...

📰 Хөндлөнгийн чухал контекст
...

📌 Өнөөдрийн чиг хандлага
• 4–7 түлхүүр сэдэв

Эх сурвалжгүй ерөнхий дүгнэлт бүү нэм.

НЭР ДЭВШИГЧ МЭДЭЭЛЭЛ:

{source_text}
""".strip()


def _create_session() -> requests.Session:
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates", [])
    if not candidates:
        raise RuntimeError(
            f"Gemini returned no candidates: {payload}"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text_parts = [
        str(part.get("text", "")).strip()
        for part in parts
        if part.get("text")
    ]
    result = "\n".join(text_parts).strip()

    if not result:
        finish_reason = candidates[0].get(
            "finishReason",
            "UNKNOWN",
        )
        raise RuntimeError(
            f"Gemini returned no text. "
            f"Finish reason: {finish_reason}"
        )

    return result


def _request_gemini(
    *,
    session: requests.Session,
    url: str,
    api_key: str,
    prompt: str,
    timeout_seconds: int,
    include_thinking: bool,
) -> requests.Response:
    generation_config: dict = {
        "maxOutputTokens": 2800,
        "temperature": 0.15,
    }

    if include_thinking:
        generation_config["thinkingConfig"] = {
            "thinkingLevel": "minimal",
        }

    return session.post(
        url,
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
            "Connection": "close",
        },
        json={
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": generation_config,
        },
        timeout=(15, timeout_seconds),
    )


def summarize_with_gemini(
    items: list[NewsItem],
    api_key: str,
    model: str,
    timeout_seconds: int = 150,
    max_summary_items: int = 15,
) -> str:
    prompt = _build_prompt(
        items,
        max_summary_items,
    )
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    tier_counts = Counter(item.trust_tier for item in items)

    print(
        f"[INFO] Gemini request: model={model}, "
        f"candidates={len(items)}, "
        f"official={tier_counts.get('official', 0)}, "
        f"research={tier_counts.get('research', 0)}, "
        f"media={tier_counts.get('media', 0)}, "
        f"community={tier_counts.get('community', 0)}",
        flush=True,
    )

    started = time.time()

    with _create_session() as session:
        response = _request_gemini(
            session=session,
            url=url,
            api_key=api_key,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            include_thinking=True,
        )

        if (
            response.status_code == 400
            and "thinking" in response.text.lower()
        ):
            print(
                "[WARN] Retrying Gemini without thinkingConfig...",
                flush=True,
            )
            response = _request_gemini(
                session=session,
                url=url,
                api_key=api_key,
                prompt=prompt,
                timeout_seconds=timeout_seconds,
                include_thinking=False,
            )

    print(
        f"[INFO] Gemini responded in "
        f"{time.time() - started:.2f} seconds.",
        flush=True,
    )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Gemini returned invalid JSON. "
            f"HTTP {response.status_code}: "
            f"{response.text[:500]}"
        ) from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini HTTP {response.status_code}: {payload}"
        )

    return _extract_text(payload)


def fallback_summary(
    items: list[NewsItem],
    max_summary_items: int = 15,
) -> str:
    today = datetime.now(
        ULAANBAATAR
    ).strftime("%Y-%m-%d")

    selected = items[:max_summary_items]
    groups = {
        "official": [],
        "research": [],
        "media": [],
        "community": [],
    }

    for item in selected:
        groups.setdefault(item.trust_tier, []).append(item)

    lines = [
        f"🤖 AI & Tech Official Daily — {today}",
        "",
        (
            "AI хураангуй түр үүсээгүй тул "
            "official-first сонголтын эх сурвалжууд:"
        ),
    ]

    labels = {
        "official": "🏢 Албан ёсны эх сурвалж",
        "research": "🧪 Судалгааны эх сурвалж",
        "media": "📰 Хөндлөнгийн технологийн хэвлэл",
        "community": "💬 Community signal",
    }

    index = 0
    for tier in ("official", "research", "media", "community"):
        tier_items = groups.get(tier, [])
        if not tier_items:
            continue

        lines.extend(["", labels[tier]])

        for item in tier_items:
            index += 1
            lines.extend(
                [
                    "",
                    f"{index}. {item.title}",
                    f"Статус: {item.status_label}",
                    f"Эх сурвалж: {item.source}",
                    item.url,
                ]
            )

    return "\n".join(lines)
