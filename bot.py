import json
import logging
import os
from pathlib import Path

from telegram import (
    Update,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

SETTINGS_FILE = Path("settings.json")
WAITING_FOR_API = 1

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# =========================
# SETTINGS
# =========================

def load_settings():
    if not SETTINGS_FILE.exists():
        return {
            "api_key": "",
            "custom_image_id": None,
        }

    try:
        return json.loads(
            SETTINGS_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return {
            "api_key": "",
            "custom_image_id": None,
        }


def save_settings(settings):
    SETTINGS_FILE.write_text(
        json.dumps(
            settings,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


settings = load_settings()


# =========================
# HELPERS
# =========================

def is_admin(update: Update):
    user = update.effective_user
    return user and user.id == OWNER_ID


def admin_keyboard():
    keyboard = [
        ["⚙️ Update API", "📊 Status"],
        ["🖼️ Upload Image", "👁️ Show Image"],
        ["🗑️ Remove Image", "❓ Help"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
    )


async def access_denied(update: Update):
    if update.message:
        await update.message.reply_text(
            "🚫 Access denied."
        )


# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await access_denied(update)
        return

    await update.message.reply_text(
        "👋 Admin Panel চালু হয়েছে।\n\n"
        "নিচের মেনু থেকে অপশন নির্বাচন করো।",
        reply_markup=admin_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await access_denied(update)
        return

    await update.message.reply_text(
        "❓ Help\n\n"
        "⚙️ Update API — API key পরিবর্তন\n"
        "📊 Status — বর্তমান সেটিংস দেখা\n"
        "🖼️ Upload Image — নতুন ছবি সংরক্ষণ\n"
        "👁️ Show Image — সংরক্ষিত ছবি দেখা\n"
        "🗑️ Remove Image — ছবি মুছে ফেলা",
        reply_markup=admin_keyboard(),
    )


# =========================
# API KEY
# =========================

async def ask_api_key(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return ConversationHandler.END

    await update.message.reply_text(
        "নতুন API key পাঠাও:"
    )

    return WAITING_FOR_API


async def save_api_key(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return ConversationHandler.END

    new_api_key = update.message.text.strip()

    if len(new_api_key) < 3:
        await update.message.reply_text(
            "❌ API key সঠিক মনে হচ্ছে না। আবার চেষ্টা করো।",
            reply_markup=admin_keyboard(),
        )
        return ConversationHandler.END

    settings["api_key"] = new_api_key
    save_settings(settings)

    masked_key = (
        f"{new_api_key[:4]}..."
        f"{new_api_key[-4:]}"
        if len(new_api_key) > 8
        else "****"
    )

    await update.message.reply_text(
        f"✅ API key সংরক্ষণ হয়েছে:\n"
        f"<code>{masked_key}</code>",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )

    return ConversationHandler.END


# =========================
# IMAGE
# =========================

async def ask_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return

    await update.message.reply_text(
        "🖼️ এখন একটি ছবি পাঠাও।"
    )


async def receive_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return

    if not update.message.photo:
        await update.message.reply_text(
            "❌ শুধু ছবি পাঠাও।",
            reply_markup=admin_keyboard(),
        )
        return

    # সবচেয়ে ভালো resolution-এর ছবি নেওয়া হচ্ছে
    photo = update.message.photo[-1]
    settings["custom_image_id"] = photo.file_id
    save_settings(settings)

    await update.message.reply_text(
        "✅ কাস্টম image সংরক্ষণ হয়েছে।",
        reply_markup=admin_keyboard(),
    )


async def show_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return

    image_id = settings.get("custom_image_id")

    if not image_id:
        await update.message.reply_text(
            "❌ কোনো image সংরক্ষিত নেই।"
        )
        return

    await update.message.reply_photo(
        photo=image_id,
        caption="🖼️ Saved Custom Image",
        reply_markup=admin_keyboard(),
    )


async def remove_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return

    settings["custom_image_id"] = None
    save_settings(settings)

    await update.message.reply_text(
        "✅ কাস্টম image মুছে ফেলা হয়েছে।",
        reply_markup=admin_keyboard(),
    )


# =========================
# STATUS
# =========================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return

    api_key = settings.get("api_key", "")
    image_id = settings.get("custom_image_id")

    if api_key:
        masked_key = (
            f"{api_key[:4]}..."
            f"{api_key[-4:]}"
            if len(api_key) > 8
            else "****"
        )
    else:
        masked_key = "Not set"

    image_status = "✅ Set" if image_id else "❌ Not set"

    await update.message.reply_text(
        "📊 <b>Admin Status</b>\n\n"
        f"👤 Owner ID: <code>{OWNER_ID}</code>\n"
        f"🔑 API Key: <code>{masked_key}</code>\n"
        f"🖼️ Custom Image: {image_status}",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )


# =========================
# MENU ROUTER
# =========================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await access_denied(update)
        return

    text = update.message.text

    if text == "⚙️ Update API":
        return await ask_api_key(update, context)

    if text == "📊 Status":
        await status(update, context)
        return

    if text == "🖼️ Upload Image":
        await ask_image(update, context)
        return

    if text == "👁️ Show Image":
        await show_image(update, context)
        return

    if text == "🗑️ Remove Image":
        await remove_image(update, context)
        return

    if text == "❓ Help":
        await help_command(update, context)
        return


# =========================
# MAIN
# =========================

def main():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    api_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^⚙️ Update API$"),
                ask_api_key,
            )
        ],
        states={
            WAITING_FOR_API: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_api_key,
                )
            ]
        },
        fallbacks=[],
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(api_conversation)

    application.add_handler(
        MessageHandler(
            filters.PHOTO & filters.User(OWNER_ID),
            receive_image,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^(📊 Status|🖼️ Upload Image|👁️ Show Image|"
                r"🗑️ Remove Image|❓ Help)$"
            ),
            menu_handler,
        )
    )

    print("Admin Panel Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()
