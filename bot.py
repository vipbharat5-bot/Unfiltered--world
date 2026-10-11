import os
import json
import asyncio
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])
DB_FILE = Path("members.json")

# Current tagging task for each group
active_tasks = {}


def load_members():
    if not DB_FILE.exists():
        return {}
    try:
        return json.loads(DB_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_members(data):
    DB_FILE.write_text(json.dumps(data))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Welcome! Use /register to opt in to group mentions."
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat or user.is_bot:
        return

    data = load_members()
    members = data.setdefault(str(chat.id), [])

    if user.id not in members:
        members.append(user.id)
        save_members(data)

    await update.effective_message.reply_text(
        "✅ Registered for group mentions. Use /unregister to opt out."
    )


async def unregister(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    data = load_members()
    key = str(chat.id)
    data[key] = [
        uid for uid in data.get(key, [])
        if uid != user.id
    ]
    save_members(data)

    await update.effective_message.reply_text(
        "✅ You have been unregistered."
    )


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
        await message.reply_text("Tagging is already running. Use /stop.")
        return

    members = load_members().get(key, [])

    if not members:
        await message.reply_text(
            "No opted-in members yet. Members can use /register."
        )
        return

    async def run_tags():
        try:
            for start_index in range(0, len(members), 5):
                batch = members[start_index:start_index + 5]

                mentions = " ".join(
                    f'<a href="tg://user?id={uid}">Member</a>'
                    for uid in batch
                )

                await context.bot.send_message(
                    chat_id=chat.id,
                    text=mentions,
                    parse_mode="HTML",
                )
                await asyncio.sleep(3)

        except asyncio.CancelledError:
            raise
        finally:
            active_tasks.pop(key, None)

    task = asyncio.create_task(run_tags())
    active_tasks[key] = task
    await message.reply_text("📣 Tagging started.")


async def gm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.effective_message

    if not user or user.id != OWNER_ID:
        await message.reply_text("⛔ Owner only.")
        return

    await message.reply_text(
        "☀️ GOOD MORNING, UNFILTERED WOULD! ❤️‍🔥"
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
        await message.reply_text("🛑 Tagging stopped.")
    else:
        await message.reply_text("No tagging is running.")


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
