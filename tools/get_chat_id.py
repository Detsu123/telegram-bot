"""Get your Telegram chat ID.

1. Create the bot with @BotFather.
2. Open your new bot and send /start.
3. Set TELEGRAM_BOT_TOKEN in your terminal.
4. Run: python tools/get_chat_id.py
"""

import json
import os
import sys

import requests


token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not token:
    print("Set TELEGRAM_BOT_TOKEN first.", file=sys.stderr)
    raise SystemExit(1)

response = requests.get(
    f"https://api.telegram.org/bot{token}/getUpdates",
    timeout=30,
)
response.raise_for_status()
payload = response.json()

if not payload.get("ok"):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(1)

results = payload.get("result", [])
if not results:
    print("No updates found. Send /start to your bot, then run this script again.")
    raise SystemExit(1)

found = []
for update in results:
    message = update.get("message") or update.get("channel_post") or {}
    chat = message.get("chat") or {}
    if "id" in chat:
        found.append(
            {
                "chat_id": chat["id"],
                "type": chat.get("type"),
                "name": chat.get("title")
                or " ".join(
                    value
                    for value in (chat.get("first_name"), chat.get("last_name"))
                    if value
                ),
            }
        )

unique = {entry["chat_id"]: entry for entry in found}
print(json.dumps(list(unique.values()), ensure_ascii=False, indent=2))
