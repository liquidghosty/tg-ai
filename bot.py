import os
import logging
from fastapi import FastAPI, Request
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)

TG_TOKEN = os.environ["TG_TOKEN"]
AI_KEY = os.environ["AI_KEY"]
AI_BASE_URL = os.environ.get("AI_BASE_URL", "https://shprotoness-ai.jq9gfk.workers.dev/v1")
AI_MODEL = os.environ.get("AI_MODEL", "mimo-v2.5")
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

client = OpenAI(api_key=AI_KEY, base_url=AI_BASE_URL)

app = FastAPI()
tg_app = ApplicationBuilder().token(TG_TOKEN).build()


async def ask_ai(prompt: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.exception("AI error")
        return f"Ошибка ИИ: {e}"


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    bot_username = context.bot.username  # без @
    text = msg.text
    is_group = msg.chat.type in ("group", "supergroup")

    # В личке — отвечаем на всё
    if not is_group:
        answer = await ask_ai(text)
        await msg.reply_text(answer)
        return

    # В группе — только если:
    # 1) упомянули @bot_username
    # 2) ответили реплаем на сообщение бота
    # 3) это команда
    mentioned = f"@{bot_username}" in text
    replied_to_bot = (
        msg.reply_to_message
        and msg.reply_to_message.from_user
        and msg.reply_to_message.from_user.id == context.bot.id
    )
    is_command = text.startswith("/")

    if not (mentioned or replied_to_bot or is_command):
        return

    # Убираем упоминание из текста перед отправкой в ИИ
    clean_text = text.replace(f"@{bot_username}", "").strip()
    if not clean_text:
        await msg.reply_text("Чего хотел?")
        return

    answer = await ask_ai(clean_text)
    await msg.reply_text(answer)


tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
tg_app.add_handler(MessageHandler(filters.COMMAND, handle))


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
