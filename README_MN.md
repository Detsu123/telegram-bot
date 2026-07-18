# AI & Technology Daily Telegram Bot

Энэ bot нь:

1. AI болон технологийн RSS/Atom эх сурвалжуудыг шалгана.
2. arXiv-ийн AI, ML, NLP, computer vision, robotics судалгааг авна.
3. Сүүлийн 36 цагийн мэдээллийг шүүнэ.
4. Өмнө явуулсан мэдээллийг дахин явуулахгүй.
5. Gemini API-аар Монгол хэлээр хураангуйлна.
6. Өдөр бүр Telegram-ийн хувийн чат руу илгээнэ.

## 1. Telegram bot үүсгэх

Telegram дээр `@BotFather`-ийг нээгээд:

1. `/newbot` гэж бич.
2. Bot-ийн нэр өг.
3. Username өг. Username нь `bot` гэж төгсөнө.
4. BotFather-аас өгсөн token-ийг нууц хадгал.
5. Шинэ bot-оо нээгээд `/start` илгээ.

Token-оо GitHub repository, Python код эсвэл чатанд шууд бичиж болохгүй.

## 2. Chat ID авах

Компьютер дээр:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Dependency суулгах:

```bash
pip install -r requirements.txt
```

Linux/macOS:

```bash
export TELEGRAM_BOT_TOKEN="BOTFATHER-ААС-АВСАН-TOKEN"
python tools/get_chat_id.py
```

Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="BOTFATHER-ААС-АВСАН-TOKEN"
python tools/get_chat_id.py
```

Гаралтаас `chat_id` утгыг хуул.

## 3. Gemini API key авах

Google AI Studio-д API key үүсгэнэ. Key-г нууц хадгал.

## 4. GitHub repository үүсгэх

1. GitHub дээр шинэ private repository үүсгэ.
2. Энэ төслийн бүх файлыг repository руу upload/push хий.
3. Repository дотроос:

`Settings → Secrets and variables → Actions → New repository secret`

Дараах гурван secret үүсгэ:

| Secret | Утга |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather token |
| `TELEGRAM_CHAT_ID` | get_chat_id.py-ийн гаргасан ID |
| `GEMINI_API_KEY` | Google AI Studio key |

## 5. Workflow-д write permission өгөх

Repository:

`Settings → Actions → General → Workflow permissions`

`Read and write permissions`-ийг сонгоод Save дар.

Энэ permission нь `seen_items.json`-г шинэчилж, нэг мэдээг дахин явуулахгүй байхад хэрэгтэй.

## 6. Эхний туршилт

Repository-ийн:

`Actions → Daily AI Tech Digest → Run workflow`

гэж ажиллуул.

Амжилттай бол Telegram руу хураангуй ирнэ.

## 7. Автомат цаг

`.github/workflows/daily.yml` одоогоор Монголын цагаар өдөр бүр 19:17-д ажиллана.

Жишээ нь 08:30 болгох:

```yaml
- cron: "30 8 * * *"
  timezone: "Asia/Ulaanbaatar"
```

## Local test

`.env` файл автоматаар уншихгүй. Environment variable-уудаа terminal дээр тохируулна:

Linux/macOS:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export GEMINI_API_KEY="..."
python main.py
```

Windows PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN="..."
$env:TELEGRAM_CHAT_ID="..."
$env:GEMINI_API_KEY="..."
python main.py
```

## Эх сурвалж өөрчлөх

`sources.py` дотор RSS source нэмнэ:

```python
{
    "name": "Source name",
    "url": "https://example.com/feed.xml",
    "base_score": 25,
},
```

Feed ажиллахгүй болсон ч бусад эх сурвалж үргэлжлэн ажиллана.

## Алдаа шалгах

GitHub repository:

`Actions → тухайн run → send-digest`

дотор log-ийг хар.

Түгээмэл алдаа:

- `Missing required environment variable` — secret буруу нэртэй эсвэл үүсээгүй.
- Telegram `401 Unauthorized` — bot token буруу.
- Telegram `400 chat not found` — bot руу `/start` илгээгүй эсвэл chat ID буруу.
- Gemini quota error — free tier limit дууссан; дараагийн өдөр дахин ажиллана, эсвэл model-оо өөрчилнө.
- Git push permission error — Workflow permissions дээр write permission өгөөгүй.

## Аюулгүй байдал

- Token болон API key-г кодонд хадгалахгүй.
- Public repository ашигласан ч secrets нь кодонд харагдахгүй, гэхдээ private repository илүү тохиромжтой.
- Token санамсаргүй ил болсон бол BotFather-аар revoke хийж шинээр ав.
