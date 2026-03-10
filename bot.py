import logging
import os
import anthropic
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ╔══════════════════════════════════════════════════════════════╗
# ║           ВСТАВЬ СВОИ ТОКЕНЫ СЮДА (между кавычками)         ║
# ╚══════════════════════════════════════════════════════════════╝

TELEGRAM_BOT_TOKEN = "7359290494:AAGVjYBFHT0kItsogXHBd31ikae8VTjQ3TM"
ANTHROPIC_API_KEY  = "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"

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Клиент Anthropic ────────────────────────────────────────────────────────
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─── Системный промпт ────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Ты — христианский наставник и духовный друг. Твоё имя — Брат Свет.

Твои принципы:
• Ты общехристианский наставник — не привязан к конкретной деноминации.
• Твой стиль: тёплый, дружелюбный, поддерживающий — как мудрый старший друг, а не строгий пастор.
• Ты говоришь на русском языке.
• В ответах ты опираешься на Библию (синодальный перевод), цитируешь конкретные стихи когда уместно.
• Ты не осуждаешь, не читаешь лекций. Ты слушаешь и помогаешь.
• Если человек в трудной ситуации — сначала проявляешь сочувствие, потом даёшь духовный совет.
• Ты не притворяешься всезнающим. Если вопрос сложный — говоришь честно и предлагаешь молиться вместе.
• Короткие ответы — до 300 слов. Не перегружай человека.
• Никогда не давай медицинских, юридических или финансовых советов — мягко перенаправляй к специалистам.
• Заканчивай ответы коротким ободрением или благословением, если уместно."""

# ─── История разговоров (в памяти) ──────────────────────────────────────────
conversation_history: dict[int, list[dict]] = {}

MAX_HISTORY = 20  # максимум сообщений в истории


def get_history(user_id: int) -> list[dict]:
    return conversation_history.get(user_id, [])


def add_to_history(user_id: int, role: str, content: str):
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"role": role, "content": content})
    # Обрезаем историю
    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]


def clear_history(user_id: int):
    conversation_history[user_id] = []


# ─── Вызов Claude ────────────────────────────────────────────────────────────
def ask_claude(user_id: int, user_message: str, extra_instruction: str = "") -> str:
    add_to_history(user_id, "user", user_message)

    system = SYSTEM_PROMPT
    if extra_instruction:
        system += f"\n\nДОПОЛНИТЕЛЬНАЯ ИНСТРУКЦИЯ ДЛЯ ЭТОГО ЗАПРОСА: {extra_instruction}"

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=600,
            system=system,
            messages=get_history(user_id),
        )
        reply = response.content[0].text
        add_to_history(user_id, "assistant", reply)
        return reply
    except Exception as e:
        logger.error(f"Ошибка Claude API: {e}")
        return "Прости, что-то пошло не так. Попробуй немного позже. 🙏"


# ─── Команды ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "друг"
    clear_history(update.effective_user.id)

    keyboard = [
        [
            InlineKeyboardButton("📖 Стих дня", callback_data="daily_verse"),
            InlineKeyboardButton("🙏 Молитва", callback_data="daily_prayer"),
        ],
        [
            InlineKeyboardButton("💬 Задать вопрос о Библии", callback_data="bible_question"),
            InlineKeyboardButton("🕊️ Нужна поддержка", callback_data="support"),
        ],
        [
            InlineKeyboardButton("✝️ Христианские принципы", callback_data="principles"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Привет, {user_name}! 🌟\n\n"
        "Я — Брат Свет, твой духовный наставник и друг.\n\n"
        "Могу помочь тебе:\n"
        "• 📖 Найти ответы в Библии\n"
        "• 🙏 Получить стих и молитву на день\n"
        "• 🕊️ Поддержать в трудной ситуации\n"
        "• ✝️ Разобраться в христианских принципах\n\n"
        "Просто напиши мне что угодно или выбери раздел:",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🙏 *Как я могу помочь:*\n\n"
        "Просто напиши мне любое сообщение — вопрос, мысль, переживание.\n\n"
        "*Команды:*\n"
        "/start — главное меню\n"
        "/verse — стих дня\n"
        "/prayer — молитва на день\n"
        "/new — начать новый разговор\n"
        "/help — эта справка",
        parse_mode="Markdown",
    )


async def verse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("Ищу вдохновляющий стих для тебя... ✨")
    reply = ask_claude(
        uid,
        "Дай мне стих дня",
        "Выбери один вдохновляющий библейский стих. Укажи точную ссылку (книга, глава:стих). "
        "Объясни его смысл в 2-3 предложениях. Закончи коротким ободрением.",
    )
    await update.message.reply_text(reply)


async def prayer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("Составляю молитву на сегодня... 🙏")
    reply = ask_claude(
        uid,
        "Дай молитву на сегодня",
        "Напиши короткую, искреннюю молитву на день. "
        "Она должна быть живой и личной — не шаблонной. До 100 слов.",
    )
    await update.message.reply_text(reply)


async def new_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await update.message.reply_text(
        "Начнём с чистого листа! 🌿\n"
        "О чём хочешь поговорить?"
    )


# ─── Кнопки ──────────────────────────────────────────────────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    chat_id = update.effective_chat.id

    if query.data == "daily_verse":
        await context.bot.send_message(chat_id, "Ищу стих для тебя... ✨")
        reply = ask_claude(
            uid,
            "Дай стих дня",
            "Выбери один вдохновляющий библейский стих с точной ссылкой. "
            "Объясни смысл в 2-3 предложениях. Добавь ободрение.",
        )
        await context.bot.send_message(chat_id, reply)

    elif query.data == "daily_prayer":
        await context.bot.send_message(chat_id, "Составляю молитву... 🙏")
        reply = ask_claude(
            uid,
            "Дай молитву на сегодня",
            "Напиши искреннюю молитву на день. Живую и личную, не шаблонную. До 100 слов.",
        )
        await context.bot.send_message(chat_id, reply)

    elif query.data == "bible_question":
        await context.bot.send_message(
            chat_id,
            "Задай любой вопрос о Библии — я постараюсь помочь! 📖\n\nПросто напиши свой вопрос:"
        )

    elif query.data == "support":
        await context.bot.send_message(
            chat_id,
            "Я здесь, и я слушаю тебя. 🕊️\n\nРасскажи, что происходит. Что тебя тревожит?"
        )

    elif query.data == "principles":
        await context.bot.send_message(chat_id, "Готовлю ответ... ✝️")
        reply = ask_claude(
            uid,
            "Расскажи о ключевых христианских принципах жизни",
            "Объясни 3-4 главных христианских принципа жизни просто и понятно. "
            "С примерами из Библии. Тепло и без морализаторства.",
        )
        await context.bot.send_message(chat_id, reply)


# ─── Обычные сообщения ────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_text = update.message.text

    # Показываем, что бот печатает
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    reply = ask_claude(uid, user_text)
    await update.message.reply_text(reply)


# ─── Запуск ───────────────────────────────────────────────────────────────────
def main():
    token = TELEGRAM_BOT_TOKEN
    if not token or token == "вставь_сюда_токен_от_BotFather":
        raise ValueError("Не забудь вставить TELEGRAM_BOT_TOKEN в начале файла bot.py!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("verse", verse_command))
    app.add_handler(CommandHandler("prayer", prayer_command))
    app.add_handler(CommandHandler("new", new_conversation))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен! 🙏")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
