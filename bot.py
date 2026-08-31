import json
import logging
import os
from pathlib import Path

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

SETTINGS_FILE = Path("settings.json")

WAITING_API_KEY = 1
WAITING_EMOJI_ID = 2


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


# =========================
# SETTINGS
# =========================

def load_settings():
    default_settings = {
        "api_key": "",
        "custom_emoji_id": "",
    }

    if not SETTINGS_FILE.exists():
        return default_settings

    try:
        data = json.loads(
            SETTINGS_FILE.read_text(encoding="utf-8")
        )

        for key, value in default_settings.items():
            data.setdefault(key, value)

        return data

    except Exception:
        return default_settings


def save_settings():
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
    return (
        update.effective_user
        and update.effective_user.id == OWNER_ID
    )


def keyboard():
    return ReplyKeyboardMarkup(
        [
            ["😀 Set Emoji ID", "👁️ Show Emoji ID"],
            ["⚙️ Update API", "📊 Status"],
            ["🧪 Test Button", "❓ Help"],
        ],
        resize_keyboard=True,
    )


async def deny(update: Update):
    if update.message:
        await update.message.reply_text(
            "🚫 Access denied."
        )


def mask_secret(value):
    if not value:
        return "Not set"

    if len(value) <= 8:
        return "****"

    return f"{value[:4]}...{value[-4:]}"


# =========================
# START / HELP
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return

    await update.message.reply_text(
        "👋 Admin Panel চালু হয়েছে।\n\n"
        "নিচের মেনু থেকে অপশন নির্বাচন করো।",
        reply_markup=keyboard(),
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await deny(update)
        return

    await update.message.reply_text(
        "❓ Help\n\n"
        "😀 Set Emoji ID — Custom Emoji ID সেট করবে\n"
        "👁️ Show Emoji ID — বর্তমান ID দেখাবে\n"
        "⚙️ Update API — API key সেট করবে\n"
        "📊 Status — সেটিংসের অবস্থা দেখাবে\n"
        "🧪 Test Button — Custom Emoji button পরীক্ষা করবে",
        reply_markup=keyboard(),
    )


# =========================
# CUSTOM EMOJI ID
# =========================

async def ask_emoji_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return ConversationHandler.END

    await update.message.reply_text(
        "😀 Custom Emoji ID পাঠাও:\n\n"
        "উদাহরণ:\n"
        "<code>5330237710655306682</code>",
        parse_mode="HTML",
    )

    return WAITING_EMOJI_ID


async def save_emoji_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return ConversationHandler.END

    emoji_id = update.message.text.strip()

    if not emoji_id.isdigit():
        await update.message.reply_text(
            "❌ ভুল ID। শুধু সংখ্যাযুক্ত Custom Emoji ID পাঠাও।",
            reply_markup=keyboard(),
        )
        return ConversationHandler.END

    settings["custom_emoji_id"] = emoji_id
    save_settings()

    await update.message.reply_text(
        "✅ Custom Emoji ID সংরক্ষণ হয়েছে:\n"
        f"<code>{emoji_id}</code>",
        parse_mode="HTML",
        reply_markup=keyboard(),
    )

    return ConversationHandler.END


async def show_emoji_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return

    emoji_id = settings.get("custom_emoji_id", "")

    if not emoji_id:
        await update.message.reply_text(
            "❌ কোনো Custom Emoji ID সেট করা নেই।",
            reply_markup=keyboard(),
        )
        return

    await update.message.reply_text(
        "😀 বর্তমান Custom Emoji ID:\n"
        f"<code>{emoji_id}</code>",
        parse_mode="HTML",
        reply_markup=keyboard(),
    )


# =========================
# API KEY
# =========================

async def ask_api_key(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return ConversationHandler.END

    await update.message.reply_text(
        "নতুন API key পাঠাও:"
    )

    return WAITING_API_KEY


async def save_api_key(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return ConversationHandler.END

    api_key = update.message.text.strip()

    if len(api_key) < 3:
        await update.message.reply_text(
            "❌ API key সঠিক নয়।",
            reply_markup=keyboard(),
        )
        return ConversationHandler.END

    settings["api_key"] = api_key
    save_settings()

    await update.message.reply_text(
        "✅ API key সংরক্ষণ হয়েছে:\n"
        f"<code>{mask_secret(api_key)}</code>",
        parse_mode="HTML",
        reply_markup=keyboard(),
    )

    return ConversationHandler.END


# =========================
# STATUS
# =========================

async def status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return

    api_key = settings.get("api_key", "")
    emoji_id = settings.get("custom_emoji_id", "")

    await update.message.reply_text(
        "📊 <b>Status</b>\n\n"
        f"👤 Owner ID: <code>{OWNER_ID}</code>\n"
        f"🔑 API Key: <code>{mask_secret(api_key)}</code>\n"
        f"😀 Emoji ID: "
        f"<code>{emoji_id or 'Not set'}</code>",
        parse_mode="HTML",
        reply_markup=keyboard(),
    )


# =========================
# TEST CUSTOM EMOJI BUTTON
# =========================

async def test_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return

    emoji_id = settings.get("custom_emoji_id", "")

    button = {
        "text": "Custom Emoji Button",
        "callback_data": "custom_emoji_test",
    }

    if emoji_id:
        button["icon_custom_emoji_id"] = emoji_id

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton.from_dict(button)]
    ])

    await update.message.reply_text(
        "🧪 Test button:",
        reply_markup=markup,
    )


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    await query.answer()

    if query.data == "custom_emoji_test":
        await query.message.reply_text(
            "✅ Custom Emoji button কাজ করছে।"
        )


# =========================
# MENU
# =========================

async def menu_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not is_admin(update):
        await deny(update)
        return

    text = update.message.text

    if text == "😀 Set Emoji ID":
        return await ask_emoji_id(update, context)

    if text == "👁️ Show Emoji ID":
        await show_emoji_id(update, context)
        return

    if text == "⚙️ Update API":
        return await ask_api_key(update, context)

    if text == "📊 Status":
        await status(update, context)
        return

    if text == "🧪 Test Button":
        await test_button(update, context)
        return

    if text == "❓ Help":
        await help_handler(update, context)


# =========================
# MAIN
# =========================

def main():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^😀 Set Emoji ID$"),
                ask_emoji_id,
            ),
            MessageHandler(
                filters.Regex(r"^⚙️ Update API$"),
                ask_api_key,
            ),
        ],
        states={
            WAITING_EMOJI_ID: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_emoji_id,
                )
            ],
            WAITING_API_KEY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_api_key,
                )
            ],
        },
        fallbacks=[],
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_handler)
    )

    application.add_handler(conversation)

    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^(👁️ Show Emoji ID|📊 Status|"
                r"🧪 Test Button|❓ Help)$"
            ),
            menu_handler,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^😀 Set Emoji ID$"),
            menu_handler,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^⚙️ Update API$"),
            menu_handler,
        )
    )

    from telegram.ext import CallbackQueryHandler

    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    print("Admin Panel Bot চলছে...")
    application.run_polling()


if __name__ == "__main__":
    main()
