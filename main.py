import logging
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- CONFIGURATION ---
BOT_TOKEN = '8313111297:AAH8w2GmI-f5fH4RW4OuzTnM8ccZ0vQ5kjA'
TARGET_GROUP_ID = -5062087509

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- BLOCK RULES ---
def is_blocked(text: str):
    if not text:
        return False

    text = text.lower()

    # ❌ block usernames
    if "@" in text:
        return True

    # ❌ block phone numbers (10 digits)
    if re.search(r"\b\d{10}\b", text):
        return True

    # ❌ block banned words
    banned_words = ["fuck", "idiot", "nude", "sex"]
    if any(word in text for word in banned_words):
        return True

    return False


# ============================================================
#  NEW FEATURE: HANDLE MESSAGES IN GROUP TAGGING THE BOT
# ============================================================
async def handle_group_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = await context.bot.get_me()
    bot_username = bot.username.lower()

    if update.effective_chat.id != TARGET_GROUP_ID:
        return

    message = update.message
    user = update.effective_user

    # --- FIX: detect tag in BOTH text and caption ---
    raw_text = (message.text or "") + " " + (message.caption or "")
    raw_text = raw_text.lower()

    if f"@{bot_username}" not in raw_text:
        return

    # Clean unwanted bot tag from text/caption
    cleaned_text = raw_text.replace(f"@{bot_username}", "").strip()

    # --------------------------------------
    #   1️⃣ Handle photos
    # --------------------------------------
    if message.photo:
        await context.bot.send_photo(
            chat_id=user.id,
            photo=message.photo[-1].file_id,
            caption="📸 Completed Request: (Your photo)"
        )
        return

    # --------------------------------------
    #   2️⃣ Handle links
    # --------------------------------------
    if message.entities:
        for entity in message.entities:
            if entity.type in ["url", "text_link"]:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"📩 Completed Request:\n\n{cleaned_text}"
                )
                return

    # --------------------------------------
    #  🚫 Invalid content → reply IN GROUP
    # --------------------------------------
    await context.bot.send_message(
        chat_id=TARGET_GROUP_ID,
        text="⚠️ please send only links or photos."
    )

# ============================================================
#   EXISTING FEATURE: USER → GROUP FORWARDING
# ============================================================
async def forward_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_chat.type == 'private':
        user = update.effective_user
        message = update.message.text or ""

        # --- 1️⃣ BLOCK CHECK ---
        if is_blocked(message):
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Your message contains restricted content and cannot be sent."
            )
            return

        try:
            logging.info(f"Received message from {user.first_name} ({user.id})")

            # Forward allowed message to group
            await context.bot.copy_message(
                chat_id=TARGET_GROUP_ID,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="We are monitoring your request and guiding it to completion"
            )

        except Exception as e:
            logging.error(f"Error forwarding message: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, an error occurred while sending your message."
            )



# ============================================================
#                        MAIN
# ============================================================
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handler for group tags → private chat
    application.add_handler(MessageHandler(filters.ChatType.GROUPS, handle_group_tag))

    # Handler for private chat messages → group forwarding
    application.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), forward_to_group))

    print("Bot is running...")
    application.run_polling()
