import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID", "-100")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found! Set in .env file")

DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///godette.db")


KARMA_COOLDOWN_SECONDS = 9
DAILY_KARMA_LIMIT = 10

MESSAGES = {
    "help": (
        "🤖 <b>Справка по боту</b>\n\n"
        "• Ответьте на сообщение пользователя знаками <code>+</code>, <code>-</code> или <code>спасибо</code>, чтобы изменить карму.\n"
        "• /top — ТОП-10 пользователей по карме\n"
        "• /stats — Ваша статистика\n"
        "• /help — Показать это сообщение"
    ),
    "self_karma": "❌ Нельзя изменять карму самому себе!",
    "bot_karma": "Нельзя изменять карму боту!",
    "cooldown": f"⏳ Вы можете изменять карму не чаще, чем раз в {KARMA_COOLDOWN_SECONDS} секунд.",
    "karma_changed": "✨ <b>{sender_name} ({sender_karma})</b> {action} карму <b>{target_name} ({target_karma})</b>",
    "daily_limit": f"⚠️ Вы исчерпали лимит изменений кармы на сегодня (максимум {DAILY_KARMA_LIMIT} раз в сутки).",
    "stats": (
        "📊 <b>Ваша статистика ({user_name}):</b>\n\n"
        "• Карма: <b>{karma}</b>\n"
        "• Отправлено сообщений: <b>{message_count}</b>"
    ),
    "top_title": "🏆 <b>ТОП-10 по карме:</b>\n",
    "top_item": "{index}. {user_name} — <b>{karma}</b> кармы",
    "top_empty": "Список лидеров пока пуст.",
}

THANK_YOU_VARIANTS = {"спасибо", "спсибо", "спс", "благодарю"}
