import os
import logging
from fastapi import FastAPI, Request
import httpx

# Ortam değişkenlerinden token al
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# FastAPI app
app = FastAPI()

# Log ayarı
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("kumkaya-bot")

# Sağlık kontrol endpoint'i
@app.get("/health")
def health():
    return {"ok": True}

# Telegram webhook endpoint'i
@app.post("/telegram/wh-7b3c6b9a")  # Environment'taki secret path ile aynı
async def telegram_webhook(request: Request):
    data = await request.json()
    log.info(f"UPDATE: {data}")

    message = data.get("message")
    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message.get("text", "")

    # Komut kontrolü
    if text.startswith("/start"):
        reply = "Merhaba! Bot aktif ✅\nBana bir ürün adı veya komut yaz."
    else:
        reply = f"Aldım: {text}"

    # Telegram'a mesaj gönder
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": reply}
        )

    return {"ok": True}
