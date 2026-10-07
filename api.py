from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session, User

app = FastAPI(title="Godette Karma API")


async def get_db():
    async with async_session() as session:
        yield session


@app.get("/api/user/{user_id}")
async def get_user_karma(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns user karma and stats by user_id.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user.user_id,
        "full_name": user.full_name,
        "karma": user.karma,
        "message_count": user.message_count,
    }
