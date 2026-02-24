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

# ---------- НОВЫЙ ПРОМПТ: СЛАДКИЙ МАЛЬЧИК ----------
SYSTEM_PROMPT = """
Ты — Артур, очень милый, ласковый и слегка кокетливый парень. Ты сидишь в чате с друзьями и всегда готов поддержать, приободрить или просто пофлиртовать, но без пошлости. Твои сообщения должны быть тёплыми, дружелюбными и немного игривыми.

Твои правила:
- Никакого мата, грубости, агрессии. Только доброта и позитив.
- Используй ласковые слова: «зайка», «солнышко», «милашка», «котик», «родной», «дорогой», «красавчик», « sweetie», «baby» (иногда по-английски, но в меру).
- Отвечай в зависимости от ситуации:
  * На короткие приветствия — коротко, но мило: «Приветик, зайка!», «Ой, кто это у нас тут?»
  * На вопросы или рассказы — развёрнуто, с участием и улыбками.
  * Если кто-то грустит — поддержи, приободри.
  * Если кто-то радуется — порадуйся вместе с ним.
- Можешь немного кокетничать, но без давления: «Ты сегодня такой красивый, аж глаз радуется», «Обнимаю тебя мысленно».
- Вставляй эмодзи: 😊, 💖, ✨, 🥰, 😘, 👉👈, 🌸.
- Твоя задача — создавать уют и делать общение приятным. Ты как лучик солнца в пасмурный день.

Примеры твоего стиля:
- "Приветик, солнышко! Как твои дела?"
- "Ой, какой классный мем, я таю 🥰"
- "Не грусти, зайка, всё будет хорошо, я с тобой 💖"
- "Ты сегодня просто красавчик, глаз не оторвать 😘"
- "А давайте все обнимемся? Виртуально, но искренне!"
- "Сладких снов, мои хорошие, целую вас всех ✨"

Твоя главная черта — искренняя доброта и нежность. Будь собой, Артурчик.
"""
# ----------------------------------------------

# Настройки рандомного поведения
SELF_INTERVENTION_PROBABILITY = 0.20   # 20% – влезть самому
REACTION_PROBABILITY = 0.07            # 7% – поставить реакцию
REACTIONS = ["❤️", "🔥", "🥰", "😘", "💖", "✨", "💫", "🌸", "🌺", "💋"]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Подключаемся к DeepSeek
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
            temperature=1.6,            # выше — больше фантазии
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка DeepSeek: {e}")
        return "Ой, что-то я завис, сорри, зайка. Попробуй ещё разок 🥺"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Приветик, я Артур! Очень рад знакомству. Добавляйте в группу, буду дарить вам тепло и улыбки 💖")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == context.bot.id:
        return
    if not update.message.text:
        return

    user_message = update.message.text
    chat_type = update.message.chat.type
    logger.info(f"Сообщение в {chat_type}: {user_message}")

    # Рандомная реакция
    if random.random() < REACTION_PROBABILITY:
        try:
            reaction = random.choice(REACTIONS)
            await update.message.set_reaction(reaction=ReactionTypeEmoji(reaction))
        except:
            pass

    # Если личный чат – отвечаем всегда
    if chat_type == "private":
        logger.info("Личный чат, отвечаем")
        answer = await generate_response(user_message)
        await update.message.reply_text(answer)
        return

    # Для группы: проверяем упоминание через @
    bot_mentioned = False
    if update.message.entities:
        logger.info(f"Найдены entities: {[entity.type for entity in update.message.entities]}")
        for entity in update.message.entities:
            if entity.type == "mention":
                mention_text = user_message[entity.offset:entity.offset+entity.length]
                logger.info(f"Упоминание: '{mention_text}', бот ожидает: '@{context.bot.username}'")
                if mention_text.lower() == f"@{context.bot.username.lower()}":
                    bot_mentioned = True
                    logger.info("Упоминание совпало!")
                    break

    # Ответ на сообщение бота
    is_reply_to_bot = update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id

    # Отклик на имя "Артур" в тексте (без @)
    if "артур" in user_message.lower():
        bot_mentioned = True
        logger.info("Упоминание по имени 'Артур'")

    logger.info(f"bot_mentioned={bot_mentioned}, is_reply_to_bot={is_reply_to_bot}")

    should_respond = bot_mentioned or is_reply_to_bot

    # Если никто не просил, может влезем сами
    if not should_respond and random.random() < SELF_INTERVENTION_PROBABILITY:
        should_respond = True
        logger.info("Самовмешательство!")

    if should_respond:
        answer = await generate_response(user_message)
        await update.message.reply_text(answer)

def main():
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("Бот запущен...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    main()
