import logging
import re
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- CONFIG ---
BOT_TOKENS = [
    '8455562528:AAEfkSpC_KtI4Tsoo0RcrNvKrHvdSOvSWno', # Bot 1
    '8455721076:AAHsNKHGXoahBe-obVEbNuKmeq7hPKc8xBg',  # Bot 2
    '8189270719:AAEU5ko6FDeqAnXsqertY5QPIA-rxd0OTHk',  # Bot 3
    '8297368951:AAGFlqhn2MGq0p7XJ3mP188yeXtCjUjqLDY',
]

TARGET_GROUP_ID = -1003324702130 

logging.basicConfig(level=logging.INFO)


# --- BLOCK RULES ---
def is_blocked(text: str):
    if not text:
        return False

    text = text.lower()
    if "@" in text: return True
    if re.search(r"\b\d{10}\b", text): return True
    if any(w in text for w in ["fuck", "idiot", "nude", "sex"]): return True
    return False


# --- GROUP TAG HANDLER ---
async def handle_group_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = await context.bot.get_me()
    bot_username = bot.username.lower()

    # Only handle messages in your group
    if update.effective_chat.id != TARGET_GROUP_ID:
        return

    message = update.message
    raw = ((message.text or "") + " " + (message.caption or "")).lower()

    if f"@{bot_username}" not in raw:
        return

    # --- HANDLE PHOTOS ---
    if message.photo:
        await context.bot.send_photo(
            chat_id=update.effective_user.id,
            photo=message.photo[-1].file_id,
            caption=f"📸 Completed Request"
        )
        return

    # --- HANDLE LINKS & SEND ACTUAL URL ---
    if message.entities:
        for ent in message.entities:
            if ent.type == "url":
                url = message.text[ent.offset : ent.offset + ent.length]
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=f"📩 Completed Request:\n\n{url}"
                )
                return

            if ent.type == "text_link":
                await context.bot.send_message(
                    chat_id=update.effective_user.id,
                    text=f"📩 Completed Request:\n\n{ent.url}"
                )
                return

    # If neither link nor photo
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        text="⚠️ please send only links or photos."
    )


# --- PRIVATE → GROUP FORWARD ---
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type != 'private':
        return

    text = update.message.text or ""
    if is_blocked(text):
        await context.bot.send_message(update.effective_chat.id,
                                       "⚠️ Your message contains restricted content.")
        return

    await context.bot.copy_message(
        chat_id=TARGET_GROUP_ID,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="We are monitoring your request..."
    )


# --- MULTI-BOT MAIN ---
async def run_bot(token):
    app = ApplicationBuilder().token(token).build()

    app.add_handler(MessageHandler(filters.ChatType.GROUPS, handle_group_tag))
    app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), forward_to_group))

    await app.initialize()
    await app.start()

    # Start polling WITHOUT await (so multiple bots can run)
    asyncio.create_task(app.updater.start_polling())

    bot = await app.bot.get_me()
    print(f"✅ Started bot: @{bot.username}")

    return app


async def main():
    print(f"Launching {len(BOT_TOKENS)} bots...\n")

    apps = [await run_bot(token) for token in BOT_TOKENS]

    # Keep alive forever
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
