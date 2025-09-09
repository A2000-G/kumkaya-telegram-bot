import os
import json
import asyncio
from typing import Dict, Any

import httpx
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from app.handlers.products import search_product

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")
WEBHOOK_SECRET_PATH = os.getenv("WEBHOOK_SECRET_PATH", "telegram/webhook")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN in environment variables.")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

app = FastAPI(title="Kumkaya Telegram Bot", version="0.1.0")


class TelegramUpdate(BaseModel):
    update_id: int | None = None
    message: Dict[str, Any] | None = None
    edited_message: Dict[str, Any] | None = None
    channel_post: Dict[str, Any] | None = None


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post(f"/{{webhook_path:path}}")
async def telegram_webhook(webhook_path: str, request: Request):
    # Only accept our configured secret path
    if webhook_path != WEBHOOK_SECRET_PATH:
        raise HTTPException(status_code=404, detail="Not found")

    payload = await request.json()
    update = TelegramUpdate.model_validate(payload)

    msg = update.message or {}
    chat = msg.get("chat") or {}
    text = (msg.get("text") or "").strip()
    chat_id = chat.get("id")

    # Basic logging (stdout JSON)
    print(json.dumps({"event": "incoming_message", "chat_id": chat_id, "text": text}, ensure_ascii=False))

    if not chat_id:
        return {"ok": True}

    # Command routing
    if text.startswith("/start"):
        reply = "Merhaba! Kumkaya ürün asistanına hoş geldiniz. /urun <isim> yazarak ürün arayabilirsiniz."
    elif text.startswith("/help"):
        reply = "Kullanım: /urun <isim>. Örn: /urun lider60"
    elif text.startswith("/kvkk"):
        reply = "KVKK: Sohbet sırasında paylaştığınız iletişim bilgileri teklif ve demo için kaydedilebilir."
    elif text.startswith("/urun"):
        q = text.replace("/urun", "", 1).strip()
        found = search_product(q)
        reply = found or "Aradığınız ürün bulunamadı. Lütfen tam adla tekrar deneyin."
    else:
        # default fallback: küçük bir eko/yardım
        found = search_product(text)
        reply = found or "Ürün aramak için /urun <isim> yazabilirsiniz."

    await send_message(chat_id, reply)
    return {"ok": True}


async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        })


@app.post("/setup-webhook")
async def setup_webhook():
    """Call once after deploy to set Telegram webhook."""
    if not WEBHOOK_BASE_URL:
        raise HTTPException(400, "WEBHOOK_BASE_URL is not set")
    url = WEBHOOK_BASE_URL.rstrip("/") + "/" + WEBHOOK_SECRET_PATH.lstrip("/")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{TELEGRAM_API}/setWebhook", json={"url": url})
        data = r.json()
        return {"requested_url": url, "telegram_response": data}
