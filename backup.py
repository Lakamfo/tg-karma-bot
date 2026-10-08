import os
import shutil
from datetime import datetime
from aiogram import Bot
from aiogram.types import FSInputFile
from config import BACKUP_CHANNEL_ID, DB_PATH


async def send_backup(bot: Bot):
    if not os.path.exists(DB_PATH):
        print(f"[{datetime.now()}] Ошибка: Файл БД '{DB_PATH}' не найден!")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename = f"godette_backup_{timestamp}.db"

    try:
        shutil.copy2(DB_PATH, backup_filename)

        document = FSInputFile(backup_filename)
        caption = (
            f"<b>Автоматический бэкап БД</b>\n"
            f"Дата: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>"
        )

        await bot.send_document(
            chat_id=BACKUP_CHANNEL_ID,
            document=document,
            caption=caption,
            parse_mode="HTML"
        )
        print(f"[{datetime.now()}] Бэкап успешно отправлен в канал!")

    except Exception as e:
        print(f"[{datetime.now()}] Ошибка при отправке бэкапа: {e}")

    finally:
        if os.path.exists(backup_filename):
            os.remove(backup_filename)