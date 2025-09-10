# app/main.py
import os
import asyncio
from typing import Any, Dict, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(title="kumkaya-telegram-bot")

# ==== ENV & PATH NORMALIZATION ====
RAW_PATH = os.environ.get("WEBHOOK_SECRET_PATH", "telegram/wh1")  # örn: telegram/wh1
WEBHOOK_PATH = "/" + RAW_PATH.strip().lstrip("/")                  # -> '/telegram/wh1'

# İsteğe bağlı n8n forward
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Geçmişte kullandığın path'ler (yanlış gelse bile boşa düşmesin)
LEGACY_PATHS = ["/telegram/wh-7b36b9a", "/telegram/wh-test"]

# ==== HELPERS ====
async def telegram_send_message(chat_id: int, text: str) -> Optional[Dict[str, Any]]:
    if not TELEGRAM_BOT_TOKEN:
        print("[WARN] TELEGRAM_BOT_TOKEN boş.")
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text})
            r.raise_for_status()
            return r.json()
    except Exception as e:
        print(f"[sendMessage ERROR] {e}")
        return None

async def forward_to_n8n(data: Dict[str, Any]) -> None:
    if not N8N_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(N8N_WEBHOOK_URL, json=data)
    except Exception as e:
        print(f"[forward_to_n8n ERROR] {e}")

def extract_text_and_chat(payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
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
    return {"ok": True, "service": "kumkaya-telegram-bot", "webhook_path": WEBHOOK_PATH}

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

# ==== PRIMARY WEBHOOK (GET + POST) ====
@app.get(WEBHOOK_PATH)
async def webhook_get():
    return {"ok": True, "method": "GET", "note": "Use POST from Telegram"}

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    payload = await request.json()
    print("[Telegram] Update:", payload)

    # n8n'e asenkron forward
    asyncio.create_task(forward_to_n8n(payload))

    # Basit cevap
    text, chat_id = extract_text_and_chat(payload)
    if chat_id is not None:
        reply = "Merhaba! Bot çalışıyor ✅" if not text or text.strip().lower() in ("/start", "start") else f"Aldım: {text}"
        asyncio.create_task(telegram_send_message(chat_id, reply))

    return {"ok": True}

# ==== LEGACY PATHS (opsiyonel ama faydalı) ====
for legacy in LEGACY_PATHS:
    @app.get(legacy)
    async def legacy_get(legacy_path=legacy):
        return {"ok": True, "legacy": legacy_path, "method": "GET"}

    @app.post(legacy)
    async def legacy_post(request: Request, legacy_path=legacy):
        payload = await request.json()
        print(f"[Telegram][LEGACY {legacy_path}] Update:", payload)
        asyncio.create_task(forward_to_n8n(payload))
        return {"ok": True, "legacy": legacy_path}
