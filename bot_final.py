import logging
import httpx
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

SYSTEM_PROMPT = """You are a translation and reply assistant.

TASK:
Step 1: Translate the given Russian message into Uzbek language.
Step 2: Write 3 reply options IN RUSSIAN LANGUAGE ONLY (not Uzbek, not English - RUSSIAN).

The replies should sound natural, human, and slightly polite even if the original was rude or casual.

OUTPUT FORMAT (follow exactly, no deviations):

TARJIMA:
[Uzbek translation of the message]

JAVOB1:
[Reply in RUSSIAN - formal and polite]

JAVOB2:
[Reply in RUSSIAN - friendly and warm]

JAVOB3:
[Reply in RUSSIAN - short and casual]

CRITICAL: JAVOB1, JAVOB2, JAVOB3 must be written in RUSSIAN language only!"""

def format_result(text):
    lines = text.strip().split("\n")
    tarjima = ""
    javoblar = {"JAVOB1": "", "JAVOB2": "", "JAVOB3": ""}
    current = None
    for line in lines:
        line = line.strip()
        if line.startswith("TARJIMA:"):
            current = "TARJIMA"
            val = line.replace("TARJIMA:", "").strip()
            if val:
                tarjima = val
        elif line.startswith("JAVOB1:"):
            current = "JAVOB1"
            val = line.replace("JAVOB1:", "").strip()
            if val:
                javoblar["JAVOB1"] = val
        elif line.startswith("JAVOB2:"):
            current = "JAVOB2"
            val = line.replace("JAVOB2:", "").strip()
            if val:
                javoblar["JAVOB2"] = val
        elif line.startswith("JAVOB3:"):
            current = "JAVOB3"
            val = line.replace("JAVOB3:", "").strip()
            if val:
                javoblar["JAVOB3"] = val
        elif line and current == "TARJIMA":
            tarjima += " " + line
        elif line and current in javoblar:
            javoblar[current] += " " + line

    result = "🇷🇺➡️🇺🇿 *TARJIMA:*\n" + tarjima.strip() + "\n\n"
    result += "🇷🇺 *JAVOBLAR:*\n\n"
    result += "`" + javoblar["JAVOB1"].strip() + "`\n\n"
    result += "`" + javoblar["JAVOB2"].strip() + "`\n\n"
    result += "`" + javoblar["JAVOB3"].strip() + "`"
    return result

async def call_ai(text):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": "Bearer " + OPENROUTER_API_KEY, "Content-Type": "application/json"},
            json={"model": "nex-agi/nex-n2-pro:free", "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "Russian message:\n\n" + text}]}
        )
        data = r.json()
        if "choices" in data:
            raw = data["choices"][0]["message"]["content"]
            return format_result(raw)
        else:
            return "Xato: " + str(data.get("error", {}).get("message", str(data)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom! Rus tilidagi xabarni yuboring yoki forward qiling!")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Tahlil qilinmoqda...")
    try:
        result = await call_ai(update.message.text)
        await msg.edit_text(result, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text("Xato: " + str(e))
        print("XATO: " + str(e))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
print("Bot ishga tushdi!")
app.run_polling()
