# KumkayaBot Starter (FastAPI + Telegram Webhook)

Profesyonel ama düşük bütçeli Telegram bot projesi için başlangıç iskeleti.

## 1) Kurulum (Local)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .env içini düzenleyin (TOKEN, BASE_URL vs.)
uvicorn app.main:app --reload
```

Health-check: http://127.0.0.1:8000/healthz

## 2) Webhook Ayarı (Prod)
Deploy ettikten sonra (Render/Railway/Docker) bir defa şu endpointi çağırın:
```bash
curl -X POST https://<your-app>/setup-webhook
```
Bu çağrı, .env içindeki `WEBHOOK_BASE_URL` ve `WEBHOOK_SECRET_PATH`’i birleştirip Telegram'a set eder.

## 3) Render (Önerilen ücretsiz başlangıç)
- Bu repo ile Render'da yeni bir Web Service oluşturun.
- `render.yaml` içindeki ayarlar yeterli.
- `WEBHOOK_BASE_URL` ve `WEBHOOK_SECRET_PATH` env değişkenlerini Render panelinden ekleyin.
- Deploy sonrası `/setup-webhook` endpointini bir defa çağırın.

## 4) Komutlar
- /start
- /help
- /urun <isim>
- /kvkk

## 5) Notlar
- `app/handlers/products.py` içinde Google Sheets araması yerine şimdilik demo var.
- Sonraki adımda Sheets entegrasyonu ve Supabase loglama eklenecek.
