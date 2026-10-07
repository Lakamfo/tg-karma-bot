import logging
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func

from config import MESSAGES, THANK_YOU_VARIANTS, KARMA_COOLDOWN_SECONDS, DAILY_KARMA_LIMIT, GROUP_ID
from database import async_session, get_or_create_user, User, KarmaLog

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handles the /help command to display bot instructions.
    """
    await message.answer(MESSAGES["help"], parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Handles the /stats command to show individual user statistics.
    """
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.full_name)
        text = MESSAGES["stats"].format(
            user_name=user.full_name,
            karma=user.karma,
            message_count=user.message_count
        )
        await message.answer(text, parse_mode="HTML")


@router.message(Command("top"))
async def cmd_top(message: Message):
    """
    Handles the /top command to show the top 10 users by karma.
    """
    async with async_session() as session:
        stmt = select(User).order_by(User.karma.desc()).limit(10)
        result = await session.execute(stmt)
        top_users = result.scalars().all()

        if not top_users:
            await message.answer(MESSAGES["top_empty"])
            return

        lines = [MESSAGES["top_title"]]
        for i, u in enumerate(top_users, start=1):
            lines.append(MESSAGES["top_item"].format(index=i, user_name=u.full_name, karma=u.karma))

        await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(F.text)
async def process_messages_and_karma(message: Message):
    """
    Increments user message counts and processes karma changes via reply triggers.
    """
    if message.chat.id != GROUP_ID:
        return
    if not message.from_user or message.from_user.is_bot:
        return

    text = message.text.strip().lower()

    # Identify karma action (+1, -1) from text triggers
    karma_change = 0
    if text == "+":
        karma_change = 1
    elif text == "-":
        karma_change = -1
    elif text in THANK_YOU_VARIANTS:
        karma_change = 1

    async with async_session() as session:
        # Update sender's total message counter
        sender = await get_or_create_user(session, message.from_user.id, message.from_user.full_name)
        sender.message_count += 1
        await session.commit()

        # Process karma logic (ONLY if trigger was met AND message is a reply)
        if karma_change != 0 and message.reply_to_message:
            target_user = message.reply_to_message.from_user

            # Restriction: Cannot give karma to a bot
            if target_user.is_bot:
                await message.reply(MESSAGES["bot_karma"])
                return

            # Restriction: Cannot modify own karma
            if target_user.id == message.from_user.id:
                await message.reply(MESSAGES["self_karma"])
                return

            now = datetime.now(timezone.utc).replace(tzinfo=None)

            # Check per-action cooldown (e.g., 1 minute)
            if sender.last_karma_given:
                delta = (now - sender.last_karma_given).total_seconds()
                if delta < KARMA_COOLDOWN_SECONDS:
                    await message.reply(MESSAGES["cooldown"])
                    return

            # Check daily rate limit (e.g., max 10 actions per 24 hours)
            day_ago = now - timedelta(days=1)
            stmt = select(func.count(KarmaLog.id)).where(
                KarmaLog.from_user_id == sender.user_id,
                KarmaLog.created_at >= day_ago
            )
            count_result = await session.execute(stmt)
            actions_last_24h = count_result.scalar_one()

            if actions_last_24h >= DAILY_KARMA_LIMIT:
                await message.reply(MESSAGES["daily_limit"])
                return

            # Apply karma adjustment to target user
            target = await get_or_create_user(session, target_user.id, target_user.full_name)
            target.karma += karma_change
            sender.last_karma_given = now

            # Log event to database history table
            karma_log = KarmaLog(
                from_user_id=sender.user_id,
                to_user_id=target.user_id,
                change=karma_change,
                chat_id=message.chat.id,
                message_id=message.message_id,
                created_at=now
            )
            session.add(karma_log)
            await session.commit()

            logger.info(
                f"[KARMA] Chat: {message.chat.id} | "
                f"From: {sender.full_name} ({sender.user_id}) -> "
                f"To: {target.full_name} ({target.user_id}) | "
                f"Change: {karma_change:+d}"
            )

            # Format and send response message
            action = "повысил" if karma_change > 0 else "понизил"
            reply_text = MESSAGES["karma_changed"].format(
                sender_name=sender.full_name,
                sender_karma=sender.karma,
                action=action,
                target_name=target.full_name,
                target_karma=target.karma
            )
            await message.reply(reply_text, parse_mode="HTML")
