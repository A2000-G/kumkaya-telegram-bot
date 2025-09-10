import os
import logging
from fastapi import FastAPI, Request
import httpx

# ── ENV ────────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]  # BotFather token (Render Environment)
API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"
N8N_URL   = os.environ.get("N8N_WEBHOOK_URL", "").strip()  # n8n Webhook Production URL

# ── APP & LOG ─────────────────────────────────────────────────────────────────
app = FastAPI()
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("kumkaya-bridge")

# ── HELPERS ───────────────────────────────────────────────────────────────────
async def send_message(chat_id: int, text: str):
    """Telegram'a basit text mesaj gönder."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{API_URL}/sendMessage",
                              json={"chat_id": chat_id, "text": text})
        # Log için kısa özet
        try:
            body = r.json()
        except Exception:
            body = {"raw": await r.aread()}
        log.debug(f"sendMessage status={r.status_code} body={body}")
        return r.status_code, body

# ── DEBUG / HEALTH ────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"ok": True, "service": "kumkaya-telegram-bridge"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/debug/getme")
async def getme():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{API_URL}/getMe")
        return r.json()

@app.get("/debug/ping-n8n")
async def ping_n8n():
    if not N8N_URL:
        return {"error": "N8N_WEBHOOK_URL tanımlı değil"}
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.post(N8N_URL, json={"message": {"text": "ping"}})
        # JSON ise json dön, değilse text
        try:
            body = r.json()
        except Exception:
            body = r.text
        return {"status": r.status_code, "body": body}

# ── TELEGRAM WEBHOOK (Telegram → Render) ──────────────────────────────────────
# ENV'deki secret path ile birebir aynı olmalı
@app.post("/telegram/wh-7b3c6b9a")
async def telegram_webhook(request: Request):
    try:
        update = await request.json()
        log.info(f"UPDATE: {update}")

        msg = update.get("message") or {}
        chat_id = (msg.get("chat") or {}).get("id")
        text = (msg.get("text") or "").strip()

        if not chat_id:
            log.warning("No chat_id in update")
            return {"ok": True}

        # 1) n8n'e ileri gönder (varsa)
        reply_text = None
        if N8N_URL:
            try:
                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(N8N_URL, json=update)
                    ct = r.headers.get("content-type", "")
                    if ct.startswith("application/json"):
                        data = r.json()
                        reply_text = (data.get("reply") or data.get("text") or "").strip()
                    else:
                        reply_text = (r.text or "").strip()
            except Exception as e:
                log.exception(f"n8n forward error: {e}")

        # 2) n8n cevap vermediyse basit fallback
        if not reply_text:
            if text.startswith("/start"):
                reply_text = "Merhaba! Bot köprü aktif ✅\nn8n bağlıysa cevabı oradan döner. Mesajınızı aldım."
            else:
                reply_text = "Aldım: " + (text or "(boş mesaj)")

        # 3) Telegram'a gönder
        await send_message(chat_id, reply_text)

    except Exception as e:
        log.exception(f"Handler error: {e}")
        # 200 dönmeye devam edelim ki Telegram retry yapmasın
    return {"ok": True}
