import os
import logging
from fastapi import FastAPI, Request
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TG_TOKEN = os.environ["TG_TOKEN"]
AI_KEY = os.environ["AI_KEY"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]  # https://твой-сервис.onrender.com

client = OpenAI(api_key=AI_KEY)

app = FastAPI()
tg_app = ApplicationBuilder().token(TG_TOKEN).build()


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": update.message.text}],
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        answer = f"Ошибка: {e}"
    await update.message.reply_text(answer)


tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))


@app.on_event("startup")
async def on_startup():
    await tg_app.initialize()
    await tg_app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logging.info("Webhook set to %s/webhook", WEBHOOK_URL)


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, tg_app.bot)
    await tg_app.process_update(update)
    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "alive"}
