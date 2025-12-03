import logging
import re
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# -------------------------------------------
#  BOT TOKENS (your bots)
# -------------------------------------------
BOT_TOKENS = [
    '8455562528:AAEfkSpC_KtI4Tsoo0RcrNvKrHvdSOvSWno',  # Bot 1
    '8455721076:AAHsNKHGXoahBe-obVEbNuKmeq7hPKc8xBg',  # Bot 2
    '8189270719:AAEU5ko6FDeqAnXsqertY5QPIA-rxd0OTHk',  # Bot 3
    '8297368951:AAGFlqhn2MGq0p7XJ3mP188yeXtCjUjqLDY',  # Bot 4
]

# -------------------------------------------
#  MANAGER MAPPING (one manager per bot)
#  Replace IDs with REAL Telegram User IDs
# -------------------------------------------
BOT_MANAGERS = {
    '8455562528:AAEfkSpC_KtI4Tsoo0RcrNvKrHvdSOvSWno': 6233082391,  # Manager 1
    '8455721076:AAHsNKHGXoahBe-obVEbNuKmeq7hPKc8xBg': 6667574477,  # Manager 2
    '8189270719:AAEU5ko6FDeqAnXsqertY5QPIA-rxd0OTHk': 6786634114,  # Manager 3
    '8297368951:AAGFlqhn2MGq0p7XJ3mP188yeXtCjUjqLDY': 8488884747,  # Manager 4
}

# -------------------------------------------
#  GROUP ID
# -------------------------------------------
TARGET_GROUP_ID = -1003324702130 

logging.basicConfig(level=logging.INFO)


# -------------------------------------------
#  TEXT BLOCK RULES
# -------------------------------------------
def is_blocked(text: str):
    if not text:
        return False

    text = text.lower()
    if "@" in text: return True
    if re.search(r"\b\d{10}\b", text): return True
    if any(w in text for w in ["fuck", "idiot", "nude", "sex"]): return True
    return False


# -------------------------------------------
#  GROUP TAG HANDLER
#  (handles @botname in group and replies to MANAGER ONLY)
# -------------------------------------------
async def handle_group_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):

    token = context.application.bot_data["token"]          # current bot token
    MANAGER_ID = BOT_MANAGERS[token]                       # manager assigned to this bot

    bot = await context.bot.get_me()
    bot_username = bot.username.lower()

    if update.effective_chat.id != TARGET_GROUP_ID:
        return

    message = update.message
    raw = ((message.text or "") + " " + (message.caption or "")).lower()

    if f"@{bot_username}" not in raw:
        return  # bot not tagged → ignore

    # --- HANDLE PHOTOS ---
    if message.photo:
        await context.bot.send_photo(
            chat_id=MANAGER_ID,
            photo=message.photo[-1].file_id,
            caption=f"📸 Completed Request"
        )
        return

    # --- HANDLE LINKS ---
    if message.entities:
        for ent in message.entities:
            if ent.type == "url":
                url = message.text[ent.offset : ent.offset + ent.length]
                await context.bot.send_message(
                    chat_id=MANAGER_ID,
                    text=f"📩 Completed Request:\n\n{url}"
                )
                return

            if ent.type == "text_link":
                await context.bot.send_message(
                    chat_id=MANAGER_ID,
                    text=f"📩 Completed Request:\n\n{ent.url}"
                )
                return

    # Not photo or link
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        text="⚠️ please send only links or photos."
    )


# -------------------------------------------
#  PRIVATE → GROUP FORWARDING
# -------------------------------------------
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    token = context.application.bot_data["token"]
    MANAGER_ID = BOT_MANAGERS[token]

    if update.effective_chat.type != 'private':
        return

    text = update.message.text or ""
    if is_blocked(text):
        await context.bot.send_message(
            update.effective_chat.id,
            "⚠️ Your message contains restricted content."
        )
        return

    # Forward to group
    await context.bot.copy_message(
        chat_id=TARGET_GROUP_ID,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id
    )

    # Notify only the manager
    await context.bot.send_message(
        chat_id=MANAGER_ID,
        text=f"📥 New Request Forwarded from user ID {update.effective_user.id}"
    )


# -------------------------------------------
#  RUN MULTIPLE BOTS
# -------------------------------------------
async def run_bot(token):
    app = ApplicationBuilder().token(token).build()

    # Store token so handlers know which manager belongs to which bot
    app.bot_data["token"] = token

    app.add_handler(MessageHandler(filters.ChatType.GROUPS, handle_group_tag))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), forward_to_group))

    await app.initialize()
    await app.start()

    asyncio.create_task(app.updater.start_polling())

    bot = await app.bot.get_me()
    print(f"✅ Started bot: @{bot.username}")

    return app


# -------------------------------------------
#  MAIN APP
# -------------------------------------------
async def main():
    print(f"Launching {len(BOT_TOKENS)} bots...\n")

    apps = [await run_bot(token) for token in BOT_TOKENS]

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
