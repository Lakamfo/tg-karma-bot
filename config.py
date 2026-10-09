import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN : str = str(os.getenv("BOT_TOKEN"))
GROUP_ID : int = int(os.getenv("GROUP_ID", "-100"))
BACKUP_CHANNEL_ID : int = int(os.getenv("BACKUP_CHANNEL_ID", "-100"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found! Set in .env file")

DB_URL : str = os.getenv("DB_URL", "sqlite+aiosqlite:///karma.db")
DB_PATH : str = os.getenv("DB_PATH", "karma.db")

API_HOST : str = os.getenv("API_HOST", "127.0.0.1")
API_PORT : int = int(os.getenv("API_PORT", 8000))

KARMA_COOLDOWN_SECONDS = 9
UNDO_TIMEOUT_SECONDS = 300
DAILY_KARMA_LIMIT = 10

MESSAGES = {
    "help": (
        "🤖 <b>Справка по боту</b>\n"
        "> Ответьте на сообщение пользователя знаками <code>+</code>, <code>-</code> или <code>спасибо</code>, чтобы изменить карму.\n"
        "> <code>/top</code> — ТОП-10 пользователей по карме\n"
        "> <code>/middle</code> — Топ пользователей (11–20 места)\n"
        "> <code>/stats</code> — Ваша статистика\n"
        "> <code>/help</code> — Показать это сообщение"
        "\n\n"
        "🔨 <b>Admin stuff</b>\n"
        "> <code>/rollback_karma</code> — Откат кармы за определенный период\n"
        "> <code>/set_karma</code> — Установка абсолютного значения кармы\n"
    ),
    "self_karma": "Нельзя изменять карму самому себе!",
    "bot_karma": "Нельзя изменять карму боту!",
    "cooldown": f"⏳ Вы можете изменять карму не чаще, чем раз в {KARMA_COOLDOWN_SECONDS} секунд.",
    "karma_changed": "<b>{sender_name} ({sender_karma})</b> {action} карму <b>{target_name} ({target_karma})</b>",
    "daily_limit": f"⚠️ Вы исчерпали лимит изменений кармы на сегодня (максимум {DAILY_KARMA_LIMIT} раз в сутки).",
    "stats": (
        "📊 <b>Статистика пользователя {user_name}:</b>\n\n"
        "> Карма: <b>{karma}</b>\n"
        "> Сообщений отправлено: <b>{message_count}</b>\n"
        "> Кармы отправил: <b>{given_count}</b> раз(а)\n"
        "> Кармы получил: <b>{received_count}</b> раз(а)"
    ),
    "negative_karma_restriction": "❌ Пользователи с отрицательной кармой не могут изменять карму другим!",
    "top_title": "🏆 <b>ТОП-10 по карме:</b>\n",
    "top_item": "{index}. {user_name} — <b>{karma}</b> кармы",
    "top_empty": "Список лидеров пока пуст.",
    "middle_top_title": "📊 <b>Топ пользователей (10–19 места):</b>\n\n{list}",
    "middle_top_empty": "ℹ️ В базе пока недостаточно пользователей для отображения этого топа.",
    "middle_top_item": "{rank}. <b>{name}</b> — {karma} кармы\n",
    "invalid_rollback_format": (
            "⚠️ <b>Неверный формат команды!</b>\n\n"
            "<b>Конкретный пользователь:</b>\n"
            "> Период за который будет откачена карма: 1m / 1h / 1d \n"
            "> Ответьте на сообщение пользователя командой <code>/rollback_karma 1h</code>\n"
            "> Или укажите ID/username: <code>/rollback_karma 1h @username</code>"
        ),
        "user_not_found": "❌ Пользователь не найден в базе данных.",
        "rollback_empty_user": "ℹ️ У пользователя <b>{user_name}</b> не найдено изменений кармы за указанный период.",
        "rollback_success_user": (
            "✅ <b>Откат кармы для пользователя {user_name} выполнен!</b>\n\n"
            "> Удалено записей: <b>{count}</b>\n"
            "> За период: <b>{time_str}</b>\n"
            "> Текущая карма пользователя: <b>{new_karma}</b>"
        ),
        "invalid_set_karma_format": (
                "⚠️ <b>Неверный формат команды!</b>\n\n"
                "Использование:\n"
                "> Ответьте на сообщение пользователя: <code>/set_karma 100</code>\n"
                "> Или укажите ID/username: <code>/set_karma 100 @username</code> или <code>/set_karma 100 123456789</code>"
            ),
            "set_karma_success": (
                "✅ <b>Карма пользователя {user_name} изменена!</b>\n\n"
                "> Предыдущая карма: <b>{old_karma}</b>\n"
                "> Новая карма: <b>{new_karma}</b>"
            ),
    "karma_undo_button": "↩️ Отменить",
    "karma_undone_alert": "Карма успешно отменена!",
    "karma_undo_not_allowed": "❌ Вы не можете отменить это действие, так как не вы изменяли карму!",
    "karma_already_undone": "⚠️ Это изменение кармы уже было отменено.",
    "karma_undone_message": "↩️ <b>{sender_name}</b> отменил(а) изменение кармы для <b>{target_name}</b>.",
}

THANK_YOU_VARIANTS = {
    "спасибо", "спсибо", "пасибо", "пасиба", "спасиб", "спасибочки", "спасибки",

    "огромное спасибо", "человеческое спасибо",

    "спс", "сяб", "спсибо",

    "благодарю", "отдуши", "от души", "благодарочка",

    "thanks", "thx", "thank you", "ty", "tnx"
}