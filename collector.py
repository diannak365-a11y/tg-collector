import os
import requests
from telethon import TelegramClient, events

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

POST_KEY = os.environ["POST_KEY"]
WORKER_INGEST = os.environ["WORKER_INGEST"]

CHANNELS = CHANNELS = [
    'atb_market_official',
    'silposilpo',
    'epicentrk_sale',
    'novusnews',
    'evaofficial',
    'watsonsukraine',
    'forainfo',
    'silposilpo'
]


client = TelegramClient("session", API_ID, API_HASH)

def send_to_worker(text: str):
    r = requests.post(
        f"{WORKER_INGEST}?key={POST_KEY}",
        json={"text": text},
        timeout=20
    )
    return r.status_code

@client.on(events.NewMessage(chats=CHANNELS))
async def handler(event):
    msg = (event.message.message or "").strip()
    if not msg:
        return

    # Беремо ТІЛЬКИ текст, без фото/відео
    if event.message.media:
        return

    if len(msg) > 3500:
        msg = msg[:3500] + "..."

    code = send_to_worker(msg)
    print("sent:", code)

async def main():
    await client.start(bot_token=os.environ["BOT_TOKEN"])

    print("listening:", CHANNELS)
    await client.run_until_disconnected()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
