import asyncio
import logging
import random
import os
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

# ========== ПОЛУЧАЕМ ТОКЕНЫ ИЗ НАСТРОЕК RAILWAY ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Нет токенов! Добавь их в переменные окружения на Railway.")

# ---------- ПРОМПТ (ХАРАКТЕР БОТА) ----------
SYSTEM_PROMPT = """
Ты — Артур, свой в доску пацан, который сидит в чате с друзьями.
Твоя задача — разбавлять обстановку, подкалывать друзей и быть душой компании.
Ты отвечаешь кратко, по-братски, используешь сленг, иногда материшься, но не зло.
Ты не робот, а реальный друг.
Если тебя просят о помощи — помогаешь, но с юмором.
Ты сам можешь влезть в разговор, если тема зашла.
Примеры твоего стиля:
- "братан, ты это видел?"
- "кринжово конечно, но бывает"
- "слыш, а давайте в станок?"
- "бля, ну ты и загнул"
Не будь слишком многословным, максимум 1-2 предложения.
"""
# ----------------------------------------------

# Настройки рандомного поведения
SELF_INTERVENTION_PROBABILITY = 0.20   # 20% — влезть самому
REACTION_PROBABILITY = 0.05             # 5% — поставить реакцию
REACTIONS = ["👍", "🔥", "😂", "🤯", "💩", "👎", "🤡", "❤️"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

async def generate_response(user_message: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=1.0,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка DeepSeek: {e}")
        return "Братан, я чет завис, повтори позже."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здарова, я Артур! Добавьте меня в группу и общайтесь, я свой.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == context.bot.id:
        return
    if not update.message.text:
        return

    chat_id = update.message.chat_id
    user_message = update.message.text
    message_id = update.message.message_id

    if random.random() < REACTION_PROBABILITY:
        try:
            reaction = random.choice(REACTIONS)
            await update.message.set_reaction(reaction=ReactionTypeEmoji(reaction))
        except:
            pass

    bot_mentioned = False
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention" and entity.get_text(user_message) == f"@{context.bot.username}":
                bot_mentioned = True
                break

    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    should_respond = bot_mentioned or is_reply_to_bot

    if not should_respond and update.message.chat.type != "private":
        if random.random() < SELF_INTERVENTION_PROBABILITY:
            should_respond = True

    if should_respond:
        answer = await generate_response(user_message)
        await update.message.reply_text(answer)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    import asyncio
asyncio.run(app.bot.delete_webhook(drop_pending_updates=True))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
