# app/main.py
import os
import asyncio
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(title="kumkaya-telegram-bot")

# ==== ENV ====
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_SECRET_PATH = os.environ.get("WEBHOOK_SECRET_PATH", "telegram/wh-test")  # örn: telegram/wh-test
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")  # örn: https://<n8n-domain>/webhook/<path>
PORT = int(os.environ.get("PORT", "8000"))

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


# ==== HELPERS ====
async def telegram_send_message(chat_id: int, text: str) -> Optional[Dict[str, Any]]:
    """Telegram'a düz metin mesaj gönder."""
    if not TELEGRAM_BOT_TOKEN:
        print("[WARN] TELEGRAM_BOT_TOKEN boş.")
        return None
    payload = {"chat_id": chat_id, "text": text}
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        print(f"[sendMessage ERROR] {e}")
        return None


async def forward_to_n8n(data: Dict[str, Any]) -> None:
    """Gelen update'i n8n webhook'una fire-and-forget ile gönder (opsiyonel)."""
    if not N8N_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(N8N_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"[forward_to_n8n ERROR] {e}")


def extract_text_and_chat(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """Update içinden text ve chat_id'yi güvenli çıkar."""
    msg = payload.get("message") or payload.get("edited_message") or {}
    if not msg and payload.get("callback_query"):
        msg = payload["callback_query"].get("message", {})
    chat = msg.get("chat", {})
    chat_id = chat.get("id")
    text = msg.get("text")
    return text, chat_id


# ==== HEALTH ====
@app.get("/")
async def root():
    return {"ok": True, "service": "kumkaya-telegram-bot", "webhook_path": f"/{WEBHOOK_SECRET_PATH}"}


@app.get("/debug/ping")
async def ping():
    return {"pong": True}


@app.get("/debug/ping-n8n")
async def ping_n8n():
    if not N8N_WEBHOOK_URL:
        return JSONResponse({"ok": False, "error": "N8N_WEBHOOK_URL not set"}, status_code=400)
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(N8N_WEBHOOK_URL, json={"message": {"text": "ping"}})
        return {"ok": True, "status": r.status_code, "body": r.text}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


# ==== TELEGRAM WEBHOOK ====
# GET'i de expose ediyoruz ki tarayıcıdan yoklama yaptığında 404 görmeyesin.
@app.get(f"/{WEBHOOK_SECRET_PATH}")
async def webhook_get():
    return {"ok": True, "method": "GET", "note": "Use POST from Telegram"}


@app.post(f"/{WEBHOOK_SECRET_PATH}")
async def telegram_webhook(request: Request):
    payload = await request.json()
    print("[Telegram] Update:", payload)

    # n8n'e asenkron forward (cevabı geciktirme)
    asyncio.create_task(forward_to_n8n(payload))

    # Basit cevaplama mantığı
    text, chat_id = extract_text_and_chat(payload)
    if chat_id is not None:
        reply = "Merhaba! Bot çalışıyor ✅"
        if text and text.strip().lower() not in ("/start", "start"):
            reply = f"Aldım: {text}"
        # Gönderimi arka planda yap (webhook 200'ü geciktirme)
        asyncio.create_task(telegram_send_message(chat_id, reply))

    # Telegram'a hızlı 200 dön (timeout yaşamamak için)
    return {"ok": True}
