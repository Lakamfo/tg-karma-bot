import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, API_HOST, API_PORT
from database import init_db
from handlers import router
from api import app
from backup import send_backup


async def start_bot():
    """Starts the Telegram bot polling and background tasks."""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        send_backup,
        trigger="interval",
        hours=24,
        kwargs={"bot": bot}
    )

    scheduler.start()
    print("🤖 Bot and APScheduler started!")

    await dp.start_polling(bot)

async def start_api():
    """Starts the FastAPI web server."""
    config = uvicorn.Config(
        app=app,
        host=API_HOST,
        port=API_PORT,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    print(f"🚀 API running on http://{API_HOST}:{API_PORT}")
    await server.serve()


async def main():
    logging.basicConfig(level=logging.INFO)

    await init_db()

    # Run Bot and API concurrently
    await asyncio.gather(
        start_bot(),
        start_api()
    )


if __name__ == "__main__":
    asyncio.run(main())