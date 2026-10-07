import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, API_HOST, API_PORT
from database import init_db
from handlers import router
from api import app


async def start_bot():
    """Starts the Telegram bot polling."""
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    print("🤖 Bot started!")
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

    # Initialize database tables
    await init_db()

    # Run Bot and API concurrently
    await asyncio.gather(
        start_bot(),
        start_api()
    )


if __name__ == "__main__":
    asyncio.run(main())
