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


def _build_prompt(items: list[NewsItem], max_summary_items: int) -> str:
    source_text = "\n\n".join(
        (
            f"[{index}]\n"
            f"TITLE: {item.title}\n"
            f"CATEGORY: {item.category}\n"
            f"SOURCE: {item.source}\n"
            f"PUBLISHED: {item.published_at}\n"
            f"IMPORTANCE_SCORE: {item.score}\n"
            f"DESCRIPTION: {item.summary[:500]}\n"
            f"URL: {item.url}"
        )
        for index, item in enumerate(items, start=1)
    )

    today = datetime.now(ULAANBAATAR).strftime("%Y-%m-%d")

    return f"""
Чи AI болон өргөн хүрээний технологийн мэдээний Монгол хэлний редактор.

Доорх нэр дэвшигч мэдээллүүдээс хамгийн чухал бөгөөд сонирхолтой
{max_summary_items}-аас ихгүй мэдээг сонгож өдөр тутмын Telegram digest бэлтгэ.

Хамруулах ангилал:
- AI модель ба судалгаа
- Software болон open-source
- Cybersecurity
- Cloud ба developer tools
- Chip, hardware, computer
- Robotics
- Space ба science
- Consumer technology
- Startup ба technology business

ДҮРЭМ:
1. Зөвхөн өгөгдсөн мэдээлэлд тулгуурла. Баримт зохиож болохгүй.
2. Нэг үйл явдлын давхардсан нийтлэлүүдийг нэг мэдээ болго.
3. Зөвхөн нэг ангиллаар дүүргэхгүй; боломжтой үед олон ангиллыг хамруул.
4. Маркетингийн хэтрүүлэг, clickbait гарчгийг энгийн болго.
5. Мэдээлэл бүрийг дараах богино хэлбэрээр бич:
   №. Гарчиг
   Юу болсон: 1–2 өгүүлбэр
   Яагаад сонирхолтой: 1 өгүүлбэр
   Хэнд хэрэгтэй: товч
   Эх сурвалж: URL
6. Open-source, код, API, model weights, benchmark-ийн тухай зөвхөн эх
   мэдээлэлд байгаа үед дурд.
7. Баталгаагүй мэдээллийг сонгохгүй; зайлшгүй сонговол
   "баталгаажаагүй" гэж тэмдэглэ.
8. Telegram Markdown ашиглахгүй. Энгийн текст хэрэглэ.
9. Нийт хариу 7000 тэмдэгтээс хэтрэхгүй.
10. Эхэнд:
🤖 AI & Tech Daily — {today}
гэсэн гарчиг тавь.
11. Дараа нь "🔥 Өдрийн онцлох 3" хэсэг гарга.
12. Үлдсэн мэдээг ангиллын нэрээр бүлэглэ.
13. Төгсгөлд:
"📌 Өнөөдрийн чиг хандлага"
гэсэн 4–7 түлхүүр сэдэв гарга.

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
        raise RuntimeError(f"Gemini returned no candidates: {payload}")

    parts = candidates[0].get("content", {}).get("parts", [])
    result = "\n".join(
        str(part.get("text", "")).strip()
        for part in parts
        if part.get("text")
    ).strip()

    if not result:
        finish_reason = candidates[0].get("finishReason", "UNKNOWN")
        raise RuntimeError(
            f"Gemini returned no text. Finish reason: {finish_reason}"
        )

    return result


def _request_gemini(
    session: requests.Session,
    url: str,
    api_key: str,
    prompt: str,
    timeout_seconds: int,
    include_thinking: bool,
) -> requests.Response:
    generation_config = {
        "maxOutputTokens": 2400,
        "temperature": 0.2,
    }
    if include_thinking:
        generation_config["thinkingConfig"] = {
            "thinkingLevel": "minimal"
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
    timeout_seconds: int = 120,
    max_summary_items: int = 15,
) -> str:
    prompt = _build_prompt(items, max_summary_items)
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    print(
        f"[INFO] Gemini request: {model}, candidates: {len(items)}",
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
        f"[INFO] Gemini responded in {time.time() - started:.2f} seconds.",
        flush=True,
    )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Gemini returned invalid JSON. HTTP "
            f"{response.status_code}: {response.text[:500]}"
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
    today = datetime.now(ULAANBAATAR).strftime("%Y-%m-%d")
    selected = items[:max_summary_items]
    category_counts = Counter(item.category for item in selected)

    lines = [
        f"🤖 AI & Tech Daily — {today}",
        "",
        "AI хураангуй түр үүсээгүй тул сонгогдсон технологийн мэдээнүүд:",
    ]

    current_category = None
    index = 0

    for item in selected:
        if item.category != current_category:
            current_category = item.category
            lines.extend(["", f"📂 {current_category}"])

        index += 1
        lines.extend(
            [
                "",
                f"{index}. {item.title}",
                f"Эх сурвалж: {item.source}",
                item.url,
            ]
        )

    lines.extend(
        [
            "",
            "Ангиллын хамрах хүрээ: "
            + ", ".join(
                f"{name} ({count})"
                for name, count in category_counts.items()
            ),
        ]
    )
    return "\n".join(lines)
