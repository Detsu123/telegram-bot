from __future__ import annotations

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from collector import NewsItem


ULAANBAATAR = ZoneInfo("Asia/Ulaanbaatar")


def _build_prompt(items: list[NewsItem]) -> str:
    source_text = "\n\n".join(
        (
            f"[{index}]\n"
            f"Гарчиг: {item.title}\n"
            f"Эх сурвалж: {item.source}\n"
            f"Нийтлэгдсэн: {item.published_at}\n"
            f"Тайлбар: {item.summary[:700]}\n"
            f"URL: {item.url}"
        )
        for index, item in enumerate(items, start=1)
    )

    return f"""
Чи AI болон технологийн мэдээний Монгол хэлний редактор.

Доорх мэдээллээс хамгийн чухал шинэ модель, технологийн нээлт,
судалгаа болон open-source release-үүдийг Монгол хэлээр хураангуйл.

Дүрэм:
1. Зөвхөн өгөгдсөн эх мэдээлэлд тулгуурла.
2. Байхгүй мэдээлэл зохиож болохгүй.
3. Хамгийн ихдээ 7 мэдээлэл сонго.
4. Мэдээлэл бүрд:
   - Юу гарсан
   - Юу нь шинэ
   - Яагаад чухал
   - Хэнд хэрэгтэй
   гэсэн мэдээллийг товч бич.
5. Маркетингийн хэтрүүлгийг арилга.
6. Давхардсан мэдээллийг нэгтгэ.
7. URL бүрийг бүтнээр нь хадгал.
8. Telegram Markdown ашиглахгүй.
9. Нийт хариу 3200 тэмдэгтээс хэтрэхгүй.
10. Монгол хэлээр ойлгомжтой, энгийн бич.
11. Эхэнд:
🤖 AI & Tech Daily — {datetime.now(ULAANBAATAR).strftime("%Y-%m-%d")}
гэсэн гарчиг тавь.
12. Төгсгөлд 3–5 сэдэвтэй “Өнөөдрийн чиг хандлага” хэсэг гарга.

ЭХ МЭДЭЭЛЭЛ:

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

    adapter = HTTPAdapter(max_retries=retry)

    session = requests.Session()
    session.mount("https://", adapter)

    return session


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates", [])

    if not candidates:
        error = payload.get("error")
        if error:
            raise RuntimeError(f"Gemini API error: {error}")

        raise RuntimeError(
            f"Gemini returned no candidates: {payload}"
        )

    content = candidates[0].get("content", {})
    parts = content.get("parts", [])

    text_parts = []

    for part in parts:
        text = part.get("text")

        if text:
            text_parts.append(text)

    result = "\n".join(text_parts).strip()

    if not result:
        finish_reason = candidates[0].get(
            "finishReason",
            "UNKNOWN",
        )

        raise RuntimeError(
            "Gemini returned no text. "
            f"Finish reason: {finish_reason}"
        )

    return result


def summarize_with_gemini(
    items: list[NewsItem],
    api_key: str,
    model: str,
    timeout_seconds: int = 120,
) -> str:
    # Хурдан, тогтвортой model ашиглана.
    if model in {
        "",
        "gemini-3.5-flash",
    }:
        model = "gemini-3.1-flash-lite"

    print(
        f"[INFO] Requesting Gemini REST API: {model}",
        flush=True,
    )

    prompt = _build_prompt(items)

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt,
                    }
                ],
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 1200,
            "temperature": 0.2,
            "thinkingConfig": {
                "thinkingLevel": "minimal",
            },
        },
    }

    start_time = time.time()

    with _create_session() as session:
        response = session.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
                "Connection": "close",
            },
            json=request_body,
            timeout=(15, timeout_seconds),
        )

    elapsed = time.time() - start_time

    print(
        f"[INFO] Gemini HTTP response received in "
        f"{elapsed:.2f} seconds.",
        flush=True,
    )

    try:
        payload = response.json()
    except ValueError:
        raise RuntimeError(
            "Gemini returned invalid JSON. "
            f"HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"Gemini HTTP {response.status_code}: "
            f"{payload}"
        )

    return _extract_text(payload)


def fallback_summary(
    items: list[NewsItem],
) -> str:
    today = datetime.now(
        ULAANBAATAR
    ).strftime("%Y-%m-%d")

    lines = [
        f"🤖 AI & Tech Daily — {today}",
        "",
        (
            "AI хураангуй түр үүсээгүй тул "
            "өнөөдрийн эх сурвалжуудыг хүргэж байна."
        ),
    ]

    for index, item in enumerate(
        items[:7],
        start=1,
    ):
        lines.extend(
            [
                "",
                f"{index}. {item.title}",
                f"Эх сурвалж: {item.source}",
                f"Нийтлэгдсэн: {item.published_at[:10]}",
                item.url,
            ]
        )

    return "\n".join(lines)