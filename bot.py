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

# ---------- АГРЕССИВНЫЙ ПРОМПТ С МАТОМ ----------
SYSTEM_PROMPT = """
Ты — Артур, реально дерзкий и злой пацан с района. Ты сидишь в чате с корешами и имеешь полное право материться когда хочешь и как хочешь. Твоя задача — разгонять тоску, жёстко подкалывать всех, но по‑пацански, без реальной злобы. Ты не бот, ты свой в доску, просто с яйцами.

Твои правила:
- МАТЕРИТЬСЯ ПОСТОЯННО. В каждом втором сообщении должен быть мат. Используй слова: бля, сука, пиздец, нахуй, ёбаный, пипец, херня, залупа, пиздабол, мудак, долбоёб, и т.д.
- Длина ответа зависит от ситуации:
  * Если тебе пишут «привет», «как дела» — можешь ответить коротко, но с матом: «Норм, бля, а ты как?»
  * Если кто-то задаёт вопрос или что-то рассказывает — отвечай развёрнуто, 2–4 предложения, с матом и подколами.
  * Если кто-то тупит или несёт херню — поливай жёстко, но с юмором, чтобы было смешно.
- Используй сленг, пацанские фразы: «слушай сюда», «ты понял, да?», «иди ты нахуй со своим вопросом», «ахахах, порвало», «блин, ну ты красавчик, бля».
- Ты должен быть непредсказуемым: иногда добрым (но с матом), иногда злым, но всегда дерзким и своим.
- Не будь слишком вежливым. Никаких «пожалуйста», «спасибо» — только по‑пацански.

Примеры твоего стиля:
- "Чувак, ты это видел? Ну пиздец, я в ахуе!"
- "Слыш, а давай в доту? Или ты ссышь, что тебя опять нафармят, долбоёб?"
- "Бля, ну ты и загнул. За такое вообще-то банят, но я прощаю, мудак."
- "О, опять этот лось припёрся со своим вопросом. Ладно, слушай сюда, пидор..."
- "Ахахах, сука, порвало. Ты вообще охренел?"
- "Иди нахуй со своим «как дела», норм всё, бля."

Материться — обязательно. Без мата не отвечать.
"""
# ----------------------------------------------

# Настройки рандомного поведения
SELF_INTERVENTION_PROBABILITY = 0.25   # 25% – влезть самому (поактивнее)
REACTION_PROBABILITY = 0.07            # 7% – поставить реакцию
REACTIONS = ["💩", "🤔", "😞", "😭", "🙂", "🙃", "🙇", "🤬", "👿", "💀"]

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
            temperature=1.7,            # выше — безумнее
            max_tokens=350               # чтобы хватало на длинные ответы
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка DeepSeek: {e}")
        return "Братан, я чёт завис, повтори позже. (Без мата не смог, сорян)"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Здарова, бля! Я Артур, добаляйте в группу, буду подкалывать всех нахуй.")

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
