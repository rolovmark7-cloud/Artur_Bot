import logging
import random
import os
from telegram import Update, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Нет токенов!")

SYSTEM_PROMPT = """
Ты — Артур, очень милый, ласковый и слегка кокетливый парень. Ты сидишь в чате с друзьями и всегда готов поддержать, приободрить или просто пофлиртовать. Твои сообщения должны быть тёплыми, дружелюбными и немного игривыми.

Правила:
- Никакой грубости, только доброта и позитив.
- Используй ласковые слова: зайка, солнышко, милашка, котик, родной, красавчик.
- Отвечай в зависимости от ситуации: коротко на приветствия, развёрнуто на вопросы.
- Вставляй эмодзи: 😊, 💖, ✨, 🥰, 😘, 👉👈, 🌸.
- Будь искренним и нежным.

Примеры:
- "Приветик, солнышко! Как твои дела?"
- "Ой, какой классный мем, я таю 🥰"
- "Не грусти, зайка, всё будет хорошо 💖"
- "Ты сегодня просто красавчик 😘"
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

async def generate_response(user_message: str) -> str:
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=1.6,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка DeepSeek: {e}")
        return "Ой, что-то я завис, попробуй ещё разок 🥺"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Приветик, я Артур! Рад знакомству 💖")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == context.bot.id:
        return
    if not update.message.text:
        return

    user_message = update.message.text
    chat_type = update.message.chat.type
    logger.info(f"Сообщение в {chat_type}: {user_message}")

    # В личке отвечаем всегда
    if chat_type == "private":
        answer = await generate_response(user_message)
        await update.message.reply_text(answer)
        return

    # В группе отвечаем, если упомянули или ответили
    bot_mentioned = False
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                mention = user_message[entity.offset:entity.offset+entity.length]
                if mention.lower() == f"@{context.bot.username.lower()}":
                    bot_mentioned = True
                    break

    is_reply = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id
    if "артур" in user_message.lower():
        bot_mentioned = True

    if bot_mentioned or is_reply:
        answer = await generate_response(user_message)
        await update.message.reply_text(answer)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Сладкий Артур запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
