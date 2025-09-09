import os
import logging
from fastapi import FastAPI, Request
import httpx

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = FastAPI()
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("kumkaya-bot")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug/getme")
async def getme():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{API_URL}/getMe")
        return r.json()

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{API_URL}/sendMessage",
                              json={"chat_id": chat_id, "text": text})
        try:
            body = r.json()
        except Exception:
            body = {"parse_error": True, "text": await r.aread()}
        log.debug(f"sendMessage status={r.status_code} body={body}")
        return r.status_code, body

@app.post("/telegram/wh-7b3c6b9a")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        log.info(f"UPDATE: {update}")

        message = update.get("message") or {}
        if not message:
            # callback_query vs. geldiğinde sessiz geç
            return {"ok": True}

        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        text = (message.get("text") or "").strip()

        if not chat_id:
            log.warning("No chat_id in update")
            return {"ok": True}

        if text.startswith("/start"):
            reply = "Merhaba! Bot aktif ✅\nBana bir ürün adı veya komut yaz."
        else:
            reply = f"Aldım: {text or '(boş mesaj)'}"

        status, body = await send_message(chat_id, reply)
        if status != 200 or not body.get("ok", False):
            log.error(f"sendMessage FAILED status={status} body={body}")

    except Exception as e:
        log.exception(f"Handler error: {e}")
        # Telegram'a 200 dönmeye devam etsin ki retry yağmasın
    return {"ok": True}
