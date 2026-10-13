import os
import json
import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])
DB_FILE = Path("members.json")

logging.basicConfig(level=logging.INFO)

active_tasks = {}


def load_members():
    if not DB_FILE.exists():
        return {}

    try:
        data = json.loads(DB_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_members(data):
    DB_FILE.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "☀️ UNFILTERED WOULD — GM BOT\n\n"
        "/register — Join mention list\n"
        "/unregister — Leave mention list\n"
        "/gm — Good Morning + mentions\n"
        "/tagall — Mention registered members\n"
        "/stop — Stop tagging\n\n"
        "Members must register before they can be mentioned."
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user or not chat or user.is_bot:
        return

    if chat.type not in ("group", "supergroup"):
        await message.reply_text("Please use /register inside your group.")
        return

    data = load_members()
    key = str(chat.id)
    members = data.setdefault(key, [])

    if user.id not in members:
        members.append(user.id)
        save_members(data)

    await message.reply_text(
        "✅ Registered for group mentions!\n"
        "Use /unregister whenever you want to opt out."
    )


async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user or not chat:
        return

    data = load_members()
    key = str(chat.id)

    data[key] = [
        uid for uid in data.get(key, [])
        if uid != user.id
    ]
    save_members(data)

    await message.reply_text("✅ You have been unregistered.")


async def run_tags(context, chat_id, key, members):
    task = asyncio.current_task()

    try:
        for index in range(0, len(members), 5):
            batch = members[index:index + 5]

            mentions = " ".join(
                f'<a href="tg://user?id={uid}">Member</a>'
                for uid in batch
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text=mentions,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )

            if index + 5 < len(members):
                await asyncio.sleep(3)

    except asyncio.CancelledError:
        raise
    except Exception:
        logging.exception("Tagging failed")
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ Tagging stopped due to a Telegram error.",
            )
        except Exception:
            logging.exception("Could not send error message")
    finally:
        if active_tasks.get(key) is task:
            active_tasks.pop(key, None)


async def tagall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user or user.id != OWNER_ID:
        await message.reply_text("⛔ Owner only.")
        return

    if not chat or chat.type not in ("group", "supergroup"):
        await message.reply_text("Use this command inside your group.")
        return

    key = str(chat.id)
    current = active_tasks.get(key)

    if current and not current.done():
        await message.reply_text("⚠️ Tagging is already running. Use /stop.")
        return

    members = load_members().get(key, [])
    members = list(dict.fromkeys(
        uid for uid in members
        if isinstance(uid, int) and not isinstance(uid, bool)
    ))

    if not members:
        await message.reply_text(
            "No registered members yet. Members can use /register."
        )
        return

    task = asyncio.create_task(
        run_tags(context, chat.id, key, members)
    )
    active_tasks[key] = task

    await message.reply_text(
        f"📣 Tagging started for {len(members)} registered members."
    )


async def gm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user or user.id != OWNER_ID:
        await message.reply_text("⛔ Owner only.")
        return

    if not chat or chat.type not in ("group", "supergroup"):
        await message.reply_text("Use /gm inside your group.")
        return

    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "☀️ GOOD MORNING, UNFILTERED WOULD! ❤️‍🔥\n\n"
            "🌅 Nayi subah, nayi energy!\n"
            "✨ Sabhi ka din shandaar rahe.\n"
            "Stay active, stay connected! 💙"
        ),
    )

    await tagall(update, context)


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user or user.id != OWNER_ID:
        await message.reply_text("⛔ Owner only.")
        return

    if not chat:
        return

    task = active_tasks.get(str(chat.id))

    if task and not task.done():
        task.cancel()
        await message.reply_text("🛑 Tagging stop requested.")
    else:
        await message.reply_text("ℹ️ No tagging is running.")


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("unregister", unregister))
    app.add_handler(CommandHandler("tagall", tagall))
    app.add_handler(CommandHandler("gm", gm))
    app.add_handler(CommandHandler("stop", stop))

    app.run_polling()


if __name__ == "__main__":
    main()
