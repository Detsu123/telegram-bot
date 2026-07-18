from __future__ import annotations

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _split_message(
    text: str,
    max_length: int = 3900,
) -> list[str]:
    text = text.strip()

    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        split_at = remaining.rfind(
            "\n\n",
            0,
            max_length,
        )

        if split_at < max_length // 2:
            split_at = remaining.rfind(
                "\n",
                0,
                max_length,
            )

        if split_at < max_length // 2:
            split_at = remaining.rfind(
                " ",
                0,
                max_length,
            )

        if split_at <= 0:
            split_at = max_length

        chunks.append(
            remaining[:split_at].strip()
        )

        remaining = remaining[
            split_at:
        ].strip()

    return chunks


def _create_session() -> requests.Session:
    retry_policy = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=2,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=frozenset(
            ["GET", "POST"]
        ),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy
    )

    session = requests.Session()

    session.mount(
        "https://",
        adapter,
    )

    session.headers.update(
        {
            "User-Agent": (
                "AI-Tech-Telegram-Bot/1.0"
            ),
            "Connection": "close",
        }
    )

    return session


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    text: str,
) -> None:
    url = (
        f"https://api.telegram.org/"
        f"bot{bot_token}/sendMessage"
    )

    session = _create_session()
    chunks = _split_message(text)

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):
        print(
            f"[INFO] Sending Telegram chunk "
            f"{index}/{len(chunks)}...",
            flush=True,
        )

        response = session.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=(15, 40),
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Telegram HTTP error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        payload = response.json()

        if not payload.get("ok"):
            raise RuntimeError(
                "Telegram rejected message: "
                f"{payload}"
            )

        if index < len(chunks):
            time.sleep(1)