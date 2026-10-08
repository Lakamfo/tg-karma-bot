import logging
import re
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, func, delete

from config import MESSAGES, THANK_YOU_VARIANTS, KARMA_COOLDOWN_SECONDS, DAILY_KARMA_LIMIT, GROUP_ID, UNDO_TIMEOUT_SECONDS
from database import async_session, get_or_create_user, User, KarmaLog, ArchivedKarmaLog

logger = logging.getLogger(__name__)
router = Router()


def parse_time_interval(interval_str: str) -> timedelta | None:
    """
    Parses strings like '30m', '2h', '1d' into a timedelta object.
    """
    match = re.match(r"^(\d+)([mhd])$", interval_str.strip().lower())
    if not match:
        return None

    value, unit = int(match.group(1)), match.group(2)
    if unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    return None


@router.callback_query(F.data.startswith("undo_karma:"))
async def process_undo_karma(callback: CallbackQuery):
    """
    Handles karma undo button clicks with a 5-minute time limit.
    """
    log_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        karma_log = await session.get(KarmaLog, log_id)

        if not karma_log:
            await callback.answer(MESSAGES["karma_already_undone"], show_alert=True)
            return

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_seconds = (now - karma_log.created_at).total_seconds()

        if elapsed_seconds > UNDO_TIMEOUT_SECONDS:
            await callback.answer(MESSAGES["karma_undo_expired"], show_alert=True)
            # Remove button from expired message
            await callback.message.edit_reply_markup(reply_markup=None)
            return

        if callback.from_user.id != karma_log.from_user_id:
            await callback.answer(MESSAGES["karma_undo_not_allowed"], show_alert=True)
            return


        target_user = await session.get(User, karma_log.to_user_id)
        sender_user = await session.get(User, karma_log.from_user_id)

        if target_user:
            target_user.karma -= karma_log.change

        await session.delete(karma_log)
        await session.commit()

        await callback.answer(MESSAGES["karma_undone_alert"])

        sender_name = sender_user.full_name if sender_user else callback.from_user.full_name
        target_name = target_user.full_name if target_user else f"User {karma_log.to_user_id}"

        edit_text = MESSAGES["karma_undone_message"].format(
            sender_name=sender_name,
            target_name=target_name
        )
        await callback.message.edit_text(edit_text, reply_markup=None, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Handles the /help command to display bot instructions.
    """
    await message.answer(MESSAGES["help"], parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """
    Handles the /stats command to show individual user statistics (own or replied user).
    """
    async with async_session() as session:
        target_from_user = None

        # Check if message is forum topic creation
        if message.reply_to_message:
            reply = message.reply_to_message
            if not reply.forum_topic_created and reply.from_user:
                target_from_user = reply.from_user

        if not target_from_user:
            target_from_user = message.from_user

        if target_from_user.is_bot:
            await message.reply(MESSAGES["bot_karma"])
            return

        user = await get_or_create_user(
            session,
            target_from_user.id,
            target_from_user.full_name
        )

        given_stmt = select(func.count(KarmaLog.id)).where(KarmaLog.from_user_id == user.user_id)
        given_result = await session.execute(given_stmt)
        given_count = given_result.scalar_one()

        received_stmt = select(func.count(KarmaLog.id)).where(KarmaLog.to_user_id == user.user_id)
        received_result = await session.execute(received_stmt)
        received_count = received_result.scalar_one()

        text = MESSAGES["stats"].format(
            user_name=user.full_name,
            karma=user.karma,
            message_count=user.message_count,
            given_count=given_count,
            received_count=received_count
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


@router.message(Command("middle"))
async def cmd_middle_top(message: Message):
    """
    Displays the top 10 users ranked from position 11 to 20 by karma.
    """

    async with async_session() as session:
        stmt = (
            select(User)
            .order_by(User.karma.desc(), User.user_id.asc())
            .offset(10)
            .limit(10)
        )
        result = await session.execute(stmt)
        users = result.scalars().all()

        if not users:
            await message.reply(MESSAGES["middle_top_empty"])
            return

        # Make list
        users_list = ""
        for index, user in enumerate(users, start=11):
            users_list += MESSAGES["middle_top_item"].format(
                rank=index,
                name=user.full_name,
                karma=user.karma
            )

        response_text = MESSAGES["middle_top_title"].format(list=users_list)
        await message.reply(response_text, parse_mode="HTML")


@router.message(Command("rollback_karma"))
async def cmd_rollback_karma(message: Message):
    """
    Admin command to roll back karma changes for a targeted user only.
    Usage:
      - Reply to user: /rollback_karma 1h
      - /rollback_karma 1h @username
      - /rollback_karma 1h 123456789
    """
    if message.chat.id != GROUP_ID:
        return

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        return

    # Extract arguments
    args = message.text.split()
    if len(args) < 2:
        await message.reply(MESSAGES["invalid_rollback_format"], parse_mode="HTML")
        return

    time_delta = parse_time_interval(args[1])
    if not time_delta:
        await message.reply(MESSAGES["invalid_rollback_format"], parse_mode="HTML")
        return

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_time = now - time_delta

    async with async_session() as session:
        target_user = None

        # Determine target user (Reply or Command argument)
        if message.reply_to_message and message.reply_to_message.from_user:
            target_user_id = message.reply_to_message.from_user.id
            target_user = await session.get(User, target_user_id)

        elif len(args) >= 3:
            user_arg = args[2].strip()
            if user_arg.isdigit():
                target_user = await session.get(User, int(user_arg))
            else:
                clean_username = user_arg.lstrip("@")
                stmt = select(User).where(User.full_name.ilike(f"%{clean_username}%"))
                result = await session.execute(stmt)
                target_user = result.scalars().first()

            if not target_user:
                await message.reply(MESSAGES["user_not_found"])
                return

        # Require a specific target user
        if not target_user:
            await message.reply(
                "❌ <b>Ошибка:</b> Не указан пользователь для отката.\n\n"
                "Ответьте на сообщение пользователя или укажите его ID/username:\n"
                "• <code>/rollback_karma 1h @username</code>\n"
                "• <code>/rollback_karma 1h 123456789</code>",
                parse_mode="HTML"
            )
            return

        # Fetch logs where target_user received karma
        stmt = select(KarmaLog).where(
            KarmaLog.to_user_id == target_user.user_id,
            KarmaLog.created_at >= cutoff_time
        )
        result = await session.execute(stmt)
        logs = result.scalars().all()

        if not logs:
            await message.reply(
                MESSAGES["rollback_empty_user"].format(user_name=target_user.full_name),
                parse_mode="HTML"
            )
            return

        # Revert target user's karma
        total_change = sum(log.change for log in logs)
        target_user.karma -= total_change

        # Archive logs before removing them from primary table
        archived_logs = [
            ArchivedKarmaLog(
                id=log.id,
                from_user_id=log.from_user_id,
                to_user_id=log.to_user_id,
                change=log.change,
                chat_id=log.chat_id,
                message_id=log.message_id,
                created_at=log.created_at,
                archived_at=now
            )
            for log in logs
        ]
        session.add_all(archived_logs)

        # Delete original logs
        delete_stmt = delete(KarmaLog).where(
            KarmaLog.to_user_id == target_user.user_id,
            KarmaLog.created_at >= cutoff_time
        )
        await session.execute(delete_stmt)
        await session.commit()

        # Send summary response
        summary = MESSAGES["rollback_success_user"].format(
            user_name=target_user.full_name,
            count=len(logs),
            time_str=args[1],
            new_karma=target_user.karma
        )
        await message.reply(summary, parse_mode="HTML")


@router.message(Command("set_karma"))
async def cmd_set_karma(message: Message):
    """
    Admin command to set absolute karma value for a specific user.
    Usage:
      - Reply to user: /set_karma 100
      - /set_karma 100 @username
      - /set_karma 100 123456789
    """
    if message.chat.id != GROUP_ID:
        return

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply(MESSAGES["invalid_set_karma_format"], parse_mode="HTML")
        return

    # Parse target karma value
    try:
        new_karma_value = int(args[1])
    except ValueError:
        await message.reply(MESSAGES["invalid_set_karma_format"], parse_mode="HTML")
        return

    async with async_session() as session:
        # Guarantee sender exists in DB for foreign key constraint in KarmaLog
        await get_or_create_user(session, message.from_user.id, message.from_user.full_name)

        target_user = None

        # Option A: Target via Reply
        if message.reply_to_message and message.reply_to_message.from_user:
            reply_user = message.reply_to_message.from_user
            target_user = await get_or_create_user(session, reply_user.id, reply_user.full_name)

        # Option B: Target via arguments (@username or user_id)
        elif len(args) >= 3:
            user_arg = args[2].strip()

            if user_arg.isdigit():
                target_id = int(user_arg)
                # Try fetching user details from chat to keep full_name updated
                try:
                    chat_member = await message.bot.get_chat_member(message.chat.id, target_id)
                    target_name = chat_member.user.full_name
                except Exception:
                    # Fallback to existing name or default if user never interacted in chat
                    existing = await session.get(User, target_id)
                    target_name = existing.full_name if existing else f"User {target_id}"

                target_user = await get_or_create_user(session, target_id, target_name)
            else:
                clean_username = user_arg.lstrip("@")
                stmt = select(User).where(User.full_name.ilike(f"%{clean_username}%"))
                result = await session.execute(stmt)
                target_user = result.scalars().first()

        if not target_user:
            await message.reply(MESSAGES["user_not_found"])
            return

        # Calculate difference and update karma
        old_karma = target_user.karma
        karma_diff = new_karma_value - old_karma

        if karma_diff == 0:
            await message.reply(
                f"ℹ️ У пользователя <b>{target_user.full_name}</b> уже установлена карма {new_karma_value}.",
                parse_mode="HTML"
            )
            return

        target_user.karma = new_karma_value
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        # Log the manual override event
        karma_log = KarmaLog(
            from_user_id=message.from_user.id,
            to_user_id=target_user.user_id,
            change=karma_diff,
            chat_id=message.chat.id,
            message_id=message.message_id,
            created_at=now
        )
        session.add(karma_log)
        await session.commit()

        # Send confirmation message
        response_text = MESSAGES["set_karma_success"].format(
            user_name=target_user.full_name,
            old_karma=old_karma,
            new_karma=new_karma_value
        )
        await message.reply(response_text, parse_mode="HTML")


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
    elif any(text.startswith(variant) for variant in THANK_YOU_VARIANTS):
        karma_change = 1

    async with async_session() as session:
        # Update sender's total message counter
        sender = await get_or_create_user(session, message.from_user.id, message.from_user.full_name)
        sender.message_count += 1
        await session.commit()

        # Process karma logic (ONLY if trigger was met AND message is a reply)
        if karma_change != 0 and message.reply_to_message:
            target_user = message.reply_to_message.from_user

            # Restriction: Users with negative karma cannot modify anyone's karma
            if sender.karma < 0:
                await message.reply(MESSAGES["negative_karma_restriction"])
                return

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

            # Format response message and inline keyboard for undo
            action = "повысил" if karma_change > 0 else "понизил"
            reply_text = MESSAGES["karma_changed"].format(
                sender_name=sender.full_name,
                sender_karma=sender.karma,
                action=action,
                target_name=target.full_name,
                target_karma=target.karma
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text=MESSAGES["karma_undo_button"],
                        callback_data=f"undo_karma:{karma_log.id}"
                    )
                ]]
            )

            await message.reply(reply_text, reply_markup=keyboard, parse_mode="HTML")
