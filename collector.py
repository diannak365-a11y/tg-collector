import os
import sys
import asyncio
import json
import time
import requests
from telethon import TelegramClient

# ---------- helpers ----------
def need_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        print(f"❌ Missing env var: {name}")
        sys.exit(1)
    return v

def env_int(name: str) -> int:
    v = need_env(name)
    try:
        return int(v)
    except ValueError:
        print(f"❌ Env var {name} must be integer, got: {v!r}")
        sys.exit(1)

# ---------- config ----------
API_ID = env_int("TG_API_ID")
API_HASH = need_env("TG_API_HASH")

# або є BOT_TOKEN, або нема — тоді просто виведемо помилку
BOT_TOKEN = os.environ.get("BOT_TOKEN")

POST_KEY = need_env("POST_KEY")
INGEST_URL = os.environ.get("INGEST_URL")

# ДЛЯ СУМІСНОСТІ: якщо десь ще використовуєш WORKER_INGEST — ок
WORKER_INGEST = os.environ.get("WORKER_INGEST") or INGEST_URL

# Канали: можна задати через ENV, щоб не правити код кожен раз
# Формат: "atb_market_official, silpo_online, ..." або через пробіл/новий рядок
channels_raw = os.environ.get("CHANNELS", "").strip()
if channels_raw:
    CHANNELS = [c.strip().lstrip("@") for c in channels_raw.replace("\n", ",").replace(" ", ",").split(",") if c.strip()]
else:
    # запасний варіант — якщо ENV не заданий
    CHANNELS = [
        "atb_market_official",
        "silpo_online",
    ]

RUN_LIMIT = int(os.environ.get("RUN_LIMIT", "10"))  # скільки постів максимум за запуск
TIMEOUT_SEC = int(os.environ.get("TIMEOUT_SEC", "60"))  # щоб Actions не висів вічно

def post_to_ingest(payload: dict):
    if not WORKER_INGEST:
        print("⚠️ No INGEST_URL/WORKER_INGEST set — skipping POST")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {POST_KEY}",
        "X-Post-Key": POST_KEY,
    }

    r = requests.post(WORKER_INGEST, headers=headers, data=json.dumps(payload), timeout=20)
    print(f"➡️ POST {WORKER_INGEST} -> {r.status_code}")
    if r.status_code >= 400:
        print("Response:", r.text[:500])
        r.raise_for_status()

async def main():
    if not BOT_TOKEN:
        print("❌ Missing BOT_TOKEN secret. Add it in Settings → Secrets and variables → Actions")
        sys.exit(1)

    # ВАЖЛИВО: session=None щоб не створювати файли сесії в Actions
    client = TelegramClient("bot_session", API_ID, API_HASH)

    await client.start(bot_token=BOT_TOKEN)
    print("✅ Bot logged in")

    total = 0
    started = time.time()

    for ch in CHANNELS:
        if time.time() - started > TIMEOUT_SEC:
            print("⏳ Time limit reached, stopping")
            break

        try:
            entity = await client.get_entity(ch)
            msgs = await client.get_messages(entity, limit=RUN_LIMIT)
            print(f"📥 {ch}: got {len(msgs)} messages")

            for m in reversed(msgs):
                if not m.message:
                    continue
                payload = {
                    "channel": ch,
                    "message_id": m.id,
                    "date": m.date.isoformat() if m.date else None,
                    "text": m.message,
                }
                post_to_ingest(payload)
                total += 1

        except Exception as e:
            print(f"⚠️ Channel {ch} error: {e}")

    await client.disconnect()
    print(f"✅ Done. Sent {total} messages. Exit OK.")

if __name__ == "__main__":
    asyncio.run(main())
