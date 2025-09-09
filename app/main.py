import os
from fastapi import FastAPI, Request
import httpx

app = FastAPI()

@app.get("/healthz")
def health():
    return {"status": "ok"}

WEBHOOK_PATH = os.environ.get("WEBHOOK_SECRET_PATH", "telegram/wh-default")
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

@app.post(f"/{WEBHOOK_PATH}")
async def telegram_webhook(req: Request):
    data = await req.json()

    msg = data.get("message") or data.get("edited_message")
    if not msg:
        return {"ok": True}

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    reply = None
    if text == "/start":
        reply = "Merhaba Ayberk! Bot çalışıyor 🚀\n\nKomutlar:\n /start\n /ping"
    elif text == "/ping":
        reply = "pong ✅"

    if reply:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                    data={"chat_id": chat_id, "text": reply},
                )
        except Exception as e:
            print("sendMessage error:", repr(e))  # <-- hata logu buraya düşecek

    return {"ok": True}
@app.get("/health")
def health():
    return {"ok": True}
