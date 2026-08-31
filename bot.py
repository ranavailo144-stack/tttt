import logging
import httpx
import asyncio
import os
import pytz 
import re      
import phonenumbers
from langdetect import detect 
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# --- CONFIGURATION (Railway Variables) ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8696233210:AAGkdcaPN4vW4htK03Gb9XTz23PoY2wjvvw")
OWNER_ID = int(os.getenv("OWNER_ID", "7414899469"))
BASE_URL = os.getenv("BASE_URL", "https://api.2oo9.cloud/MXS47FLFX0U/tnevs/@public/api")

# ⭐️ আপনার অরিজিনাল টেলিগ্রাম ও হোয়াটসঅ্যাপ ৩ডি লোগোর আইডি
TG_BTN_EMOJI_ID = "5330237710655306682"  # আসল টেলিগ্রাম লোগো
WA_BTN_EMOJI_ID = "5427009714745517609"  # আসল হোয়াটসঅ্যাপ লোগো

# মেসেজ বক্সের ভেতরের জন্য কাস্টম ইমোজি
TG_REAL_LOGO = f'<tg-emoji emoji-id="{TG_BTN_EMOJI_ID}">✈️</tg-emoji>'
WA_REAL_LOGO = f'<tg-emoji emoji-id="{WA_BTN_EMOJI_ID}">🟢</tg-emoji>'

# ডিফল্ট সেটিংস
current_api_key = "MTWFKHLKHQI"
TG_ENABLED = True  
WA_ENABLED = False 

BD_TZ = pytz.timezone('Asia/Dhaka')
WAITING_FOR_API = 1
WAITING_FOR_TG_EMOJI = 2
WAITING_FOR_WA_EMOJI = 3

headers_template = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

sent_hits = set() 
hit_history = []  
deletion_queue = []

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- HELPER FUNCTIONS ---
def get_flag_emoji(country_code):
    if not country_code: return "🏳️"
    return "".join(chr(127397 + ord(c)) for c in country_code.upper())

def get_country_details(phone_number):
    try:
        digits_only = re.sub(r'\D', '', phone_number)
        parsed_number = phonenumbers.parse("+" + digits_only, None)
        region_code = phonenumbers.region_code_for_number(parsed_number)
        if region_code:
            flag = get_flag_emoji(region_code)
            return region_code, flag
    except Exception:
        pass
    return "GT", "🇬🇹"

def detect_language_name(text):
    try:
        clean_text = re.sub(r'\d+', '', text)
        if len(clean_text.strip()) < 3:
            return "English"
        lang_code = detect(text)
        lang_names = {
            'fr': 'French', 'en': 'English', 'ar': 'Arabic', 'bn': 'Bengali',
            'es': 'Spanish', 'pt': 'Portuguese', 'ru': 'Russian', 'de': 'German'
        }
        return lang_names.get(lang_code, "English")
    except Exception:
        return "English"

def extract_only_code(text):
    if not text:
        return "N/A"
    match = re.search(r'\b\d+(?:-\d+)?\b', text)
    if match:
        return match.group(0)
    cleaned = re.sub(r'^(Telegram|WhatsApp)?\s*(code|verification code)?\s*[:\-\s]*', '', text, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else text

def get_headers():
    headers = headers_template.copy()
    headers["mauthapi"] = current_api_key
    return headers

def get_main_keyboard():
    keyboard = [
        [
            KeyboardButton("⚙️ Update API", api_kwargs={"style": "primary"}),
            KeyboardButton("📊 Status", api_kwargs={"style": "success"})
        ],
        [
            KeyboardButton("🔘 TG: ON/OFF", api_kwargs={"style": "primary"}),
            KeyboardButton("🔘 WA: ON/OFF", api_kwargs={"style": "danger"})
        ],
        [
            KeyboardButton("🖼️ TG Emoji", api_kwargs={"style": "primary"}),
            KeyboardButton("🖼️ WA Emoji", api_kwargs={"style": "primary"})
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ⭐️ পারফেক্ট কালারফুল ইনলাইন বাটন (অরিজিনাল ইমোজি আইডি সহ)
async def send_colored_hit(chat_id, text, otp_code, lang_name, btn_emoji_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    inline_keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": f" {lang_name}",
                    "icon_custom_emoji_id": btn_emoji_id,
                    "style": "success",
                    "copy_text": {"text": str(otp_code)}
                },
                {
                    "text": f"{otp_code}",
                    "style": "primary",
                    "copy_text": {"text": str(otp_code)}
                }
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": inline_keyboard
    }
    
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=payload, timeout=10)
        return res.json()

# --- BACKGROUND MONITOR ---
async def traffic_monitor(application):
    global sent_hits, current_api_key, TG_ENABLED, WA_ENABLED, hit_history
    print("🚀 Traffic Monitor Running (Premium Style)...")
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                now = datetime.now(BD_TZ)
                response = await client.get(f"{BASE_URL}/console", headers=get_headers(), timeout=10)
                data = response.json()
                
                if data.get('meta', {}).get('code') == 200:
                    hits = data.get('data', {}).get('hits', [])
                    for hit in hits:
                        sid = hit.get('sid', 'Unknown').lower()
                        range_id = hit.get('range', 'Unknown')
                        msg_text = hit.get('message', 'No message')
                        
                        should_send = False
                        real_logo = TG_REAL_LOGO
                        btn_emoji_id = TG_BTN_EMOJI_ID
                        service_name = "Telegram"

                        if sid == "telegram" and TG_ENABLED:
                            should_send = True
                            real_logo = TG_REAL_LOGO
                            btn_emoji_id = TG_BTN_EMOJI_ID
                            service_name = "Telegram"
                        elif sid == "whatsapp" and WA_ENABLED:
                            should_send = True
                            real_logo = WA_REAL_LOGO
                            btn_emoji_id = WA_BTN_EMOJI_ID
                            service_name = "WhatsApp"

                        if should_send:
                            hit_id = f"{range_id}_{msg_text}"
                            if hit_id not in sent_hits:
                                hit_history.append({'service': service_name, 'time': now})
                                
                                iso_code, flag = get_country_details(range_id)
                                lang = detect_language_name(msg_text)
                                clean_code = extract_only_code(msg_text)

                                # ⭐️ আপনার পছন্দের প্রিমিয়াম ডিজাইন
                                final_text = (
                                    f"✨ <b>{service_name}</b> ✨\n"
                                    f"╭─────────────────\n"
                                    f"│ {flag} <b>{iso_code}</b> {real_logo} <code>{range_id}</code>\n"
                                    f"╰─────────────────"
                                )
                                
                                send_res = await send_colored_hit(OWNER_ID, final_text, clean_code, lang, btn_emoji_id)
                                
                                if send_res.get("ok"):
                                    msg_id = send_res["result"]["message_id"]
                                    deletion_queue.append((OWNER_ID, msg_id, now + timedelta(minutes=2)))
                                
                                sent_hits.add(hit_id)

                cutoff_time = now - timedelta(hours=24)
                hit_history[:] = [h for h in hit_history if h['time'] > cutoff_time]
                if len(sent_hits) > 1000: sent_hits.clear()

                for item in deletion_queue[:]:
                    chat_id, msg_id, d_time = item
                    if now >= d_time:
                        try: 
                            await application.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        except: 
                            pass
                        deletion_queue.remove(item)

            except Exception:
                pass
            
            await asyncio.sleep(5)

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("🚫 <b>ACCESS DENIED!</b>", parse_mode="HTML")
        return 
    
    await update.message.reply_text(
        "👋 <b>Hello Boss!</b>\n\nTraffic Monitor is successfully connected and active.", 
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_api_key, TG_ENABLED, WA_ENABLED, hit_history
    if update.effective_user.id != OWNER_ID: return 
    text = update.message.text
    now = datetime.now(BD_TZ)
    
    if text == "📊 Status":
        current_hour_start = now.replace(minute=0, second=0, microsecond=0)
        
        tg_hits = sum(1 for h in hit_history if h['service'] == "Telegram" and h['time'] >= current_hour_start)
        wa_hits = sum(1 for h in hit_history if h['service'] == "WhatsApp" and h['time'] >= current_hour_start)
        
        current_hour_str = now.strftime('%I:00 %p')
        
        tg_status = f"✅ ON | 📦 Hits: <code>{tg_hits}</code>" if TG_ENABLED else "❌ OFF"
        wa_status = f"✅ ON | 📦 Hits: <code>{wa_hits}</code>" if WA_ENABLED else "❌ OFF"
        
        status_msg = (
            f"✅ <b>Bot Status: Running Fast! 🚀</b>\n"
            f"✈️ <b>Telegram:</b> {tg_status}\n"
            f"🟢 <b>WhatsApp:</b> {wa_status}\n"
            f"⏳ <b>Current Hour:</b> <code>Since {current_hour_str}</code>\n"
            f"🔑 <b>API:</b> <code>{current_api_key[:5]}...{current_api_key[-5:]}</code>\n"
            f"⏰ <b>BD Time:</b> <code>{now.strftime('%I:%M:%S %p')}</code>\n"
            f"🖼️ <b>TG Emoji ID:</b> <code>{TG_BTN_EMOJI_ID}</code>\n"
            f"🖼️ <b>WA Emoji ID:</b> <code>{WA_BTN_EMOJI_ID}</code>"
        )
        await update.message.reply_text(status_msg, reply_markup=get_main_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    elif text == "🔘 TG: ON/OFF":
        TG_ENABLED = not TG_ENABLED
        await update.message.reply_text(f"✈️ <b>Telegram is now {'ON' if TG_ENABLED else 'OFF'}!</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    elif text == "🔘 WA: ON/OFF":
        WA_ENABLED = not WA_ENABLED
        await update.message.reply_text(f"🟢 <b>WhatsApp is now {'ON' if WA_ENABLED else 'OFF'}!</b>", reply_markup=get_main_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    elif text == "⚙️ Update API":
        await update.message.reply_text("📩 Please send the <b>New API Key</b> now:", parse_mode="HTML")
        return WAITING_FOR_API
        
    elif text == "🖼️ TG Emoji":
        await update.message.reply_text("📩 Please send the <b>New Telegram Emoji ID</b> now:", parse_mode="HTML")
        return WAITING_FOR_TG_EMOJI
        
    elif text == "🖼️ WA Emoji":
        await update.message.reply_text("📩 Please send the <b>New WhatsApp Emoji ID</b> now:", parse_mode="HTML")
        return WAITING_FOR_WA_EMOJI

async def update_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_api_key
    if update.effective_user.id != OWNER_ID: return 
    current_api_key = update.message.text.strip()
    await update.message.reply_text(f"✅ <b>API Key Updated:</b> <code>{current_api_key}</code>", reply_markup=get_main_keyboard(), parse_mode="HTML")
    return ConversationHandler.END

async def update_tg_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TG_BTN_EMOJI_ID, TG_REAL_LOGO
    if update.effective_user.id != OWNER_ID: return 
    TG_BTN_EMOJI_ID = update.message.text.strip()
    TG_REAL_LOGO = f'<tg-emoji emoji-id="{TG_BTN_EMOJI_ID}">✈️</tg-emoji>'
    await update.message.reply_text(f"✅ <b>TG Emoji ID Updated:</b> <code>{TG_BTN_EMOJI_ID}</code>", reply_markup=get_main_keyboard(), parse_mode="HTML")
    return ConversationHandler.END

async def update_wa_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global WA_BTN_EMOJI_ID, WA_REAL_LOGO
    if update.effective_user.id != OWNER_ID: return 
    WA_BTN_EMOJI_ID = update.message.text.strip()
    WA_REAL_LOGO = f'<tg-emoji emoji-id="{WA_BTN_EMOJI_ID}">🟢</tg-emoji>'
    await update.message.reply_text(f"✅ <b>WA Emoji ID Updated:</b> <code>{WA_BTN_EMOJI_ID}</code>", reply_markup=get_main_keyboard(), parse_mode="HTML")
    return ConversationHandler.END

async def post_init(application):
    asyncio.create_task(traffic_monitor(application))

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(⚙️ Update API|🖼️ TG Emoji|🖼️ WA Emoji)$"), handle_menu)],
        states={
            WAITING_FOR_API: [MessageHandler(filters.TEXT & (~filters.COMMAND), update_api_key)],
            WAITING_FOR_TG_EMOJI: [MessageHandler(filters.TEXT & (~filters.COMMAND), update_tg_emoji)],
            WAITING_FOR_WA_EMOJI: [MessageHandler(filters.TEXT & (~filters.COMMAND), update_wa_emoji)]
        },
        fallbacks=[],
    )
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^(📊 Status|🔘 TG: ON/OFF|🔘 WA: ON/OFF)$"), handle_menu))
    
    print("Bot is successfully running...")
    application.run_polling()
