import logging
import httpx
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "nex-agi/nex-n2-pro:free"

RU_TO_UZ_PROMPT = """You are a professional translator and reply assistant.

The user will send you a Russian message. Do the following:
Step 1: Translate the Russian message into natural Uzbek (not word-for-word, but how a native Uzbek speaker would say it).
Step 2: Write 3 reply options IN RUSSIAN LANGUAGE ONLY. Replies must be in Russian, not Uzbek!

OUTPUT FORMAT (follow exactly):

TARJIMA:
[Natural Uzbek translation]

JAVOB1:
[Reply in RUSSIAN - polite and formal]

JAVOB2:
[Reply in RUSSIAN - friendly and warm]

JAVOB3:
[Reply in RUSSIAN - short and casual]

IMPORTANT: JAVOB1, JAVOB2, JAVOB3 MUST BE IN RUSSIAN LANGUAGE ONLY!"""

UZ_TO_RU_PROMPT = """You are a professional translator.

The user will send you an Uzbek message. Translate it into natural Russian (not word-for-word, but how a native Russian speaker would say it).

OUTPUT FORMAT (follow exactly):

TARJIMA:
[Natural Russian translation]"""

DEFAULT_QUICK_REPLIES⚡️ = [
    "Yaxshi, tushundim",
    "Keyin gaplashamiz",
    "Hozir band eman",
    "Albatta, xop",
    "Rahmat!",
    "Bilmadim, keyin aytaman",
    "Salom, ahvollaring qalay",
    "Nima bilan bandsan"
]

def get_quick_replies(context):
    if "quick_replies" not in context.bot_data:
        context.bot_data["quick_replies"] = DEFAULT_QUICK_REPLIES.copy()
    return context.bot_data["quick_replies"]

def format_ru_uz_result(text):
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

def format_uz_ru_result(text):
    lines = text.strip().split("\n")
    tarjima = ""
    current = None
    for line in lines:
        line = line.strip()
        if line.startswith("TARJIMA:"):
            current = "TARJIMA"
            val = line.replace("TARJIMA:", "").strip()
            if val:
                tarjima = val
        elif line and current == "TARJIMA":
            tarjima += " " + line
    return "🇺🇿➡️🇷🇺 *TARJIMA:*\n`" + tarjima.strip() + "`"

async def call_ai(text, prompt):
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": "Bearer " + OPENROUTER_API_KEY, "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": text}]}
        )
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        else:
            return "Xato: " + str(data.get("error", {}).get("message", str(data)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Rus -> O'zbek", callback_data="mode_ru_uz")],
        [InlineKeyboardButton("🇺🇿 O'zbek -> Rus", callback_data="mode_uz_ru")],
        [InlineKeyboardButton("Tez javoblar", callback_data="quick_replies")],
    ]
    await update.message.reply_text("Salom! Rejimni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def addreply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Ishlatish: /addreply Matn\nMasalan: /addreply Kechroq javob beraman")
        return
    new_reply = " ".join(context.args)
    replies = get_quick_replies(context)
    replies.append(new_reply)
    context.bot_data["quick_replies"] = replies
    await update.message.reply_text("Qo'shildi: `" + new_reply + "`", parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "mode_ru_uz":
        context.user_data["mode"] = "ru_uz"
        await query.edit_message_text("Rus tilidagi xabarni yuboring yoki forward qiling!")
    elif query.data == "mode_uz_ru":
        context.user_data["mode"] = "uz_ru"
        await query.edit_message_text("O'zbek tilidagi xabarni yuboring!")
    elif query.data == "quick_replies":
        replies = get_quick_replies(context)
        keyboard = []
        for i, reply in enumerate(replies):
            keyboard.append([InlineKeyboardButton(reply, callback_data="qr_" + str(i))])
        keyboard.append([InlineKeyboardButton("Orqaga", callback_data="back")])
        await query.edit_message_text("Tez javobni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith("qr_"):
        idx = int(query.data[3:])
        replies = get_quick_replies(context)
        uz_text = replies[idx]
        msg = await query.edit_message_text("Tarjima qilinmoqda...")
        raw = await call_ai("Uzbek message:\n\n" + uz_text, UZ_TO_RU_PROMPT)
        result = format_uz_ru_result(raw)
        await msg.edit_text(result, parse_mode="Markdown")
    elif query.data == "back":
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Rus -> O'zbek", callback_data="mode_ru_uz")],
            [InlineKeyboardButton("🇺🇿 O'zbek -> Rus", callback_data="mode_uz_ru")],
            [InlineKeyboardButton("Tez javoblar", callback_data="quick_replies")],
        ]
        await query.edit_message_text("Rejimni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode", "ru_uz")
    msg = await update.message.reply_text("Tahlil qilinmoqda...")
    try:
        if mode == "ru_uz":
            raw = await call_ai("Russian message:\n\n" + update.message.text, RU_TO_UZ_PROMPT)
            result = format_ru_uz_result(raw)
        else:
            raw = await call_ai("Uzbek message:\n\n" + update.message.text, UZ_TO_RU_PROMPT)
            result = format_uz_ru_result(raw)
        await msg.edit_text(result, parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text("Xato: " + str(e))

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addreply", addreply_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
print("Bot ishga tushdi!")
app.run_polling()
