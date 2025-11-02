import os
import json
import random
import datetime
import pytz
import threading
from flask import Flask
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ======== Flask Web Server to keep Render alive ========
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ My Errand Guy Bot is alive and running!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

# ======== Telegram Bot Setup ========
BOT_TOKEN = os.getenv("BOT_TOKEN")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "MyErrandGuy")

# ======== Google Sheets Auth ========
creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

# ======== Helper Functions ========
def generate_errand_id():
    today = datetime.datetime.now().strftime("%Y%m%d")
    existing = sheet.get_all_values()
    count_today = sum(1 for row in existing if today in row[0])
    return f"ERR-{today}-{count_today + 1:03}"

def generate_otp():
    return str(random.randint(1000, 9999))

# ======== Telegram Bot Commands ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to My Errand Guy Bot!\n\n"
        "Use this command to log a new errand:\n"
        "/newerrand pickup dropoff sender receiver\n\n"
        "Example:\n"
        "/newerrand Windhoek_MaeruaMall Rehoboth_Junction John_Doe Mary_Smith",
        parse_mode="Markdown"
    )

async def new_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 4:
            await update.message.reply_text("⚠ Please provide pickup, dropoff, sender, and receiver.")
            return

        pickup, dropoff, sender, receiver = context.args[:4]
        timestamp = datetime.datetime.now(pytz.timezone("Africa/Windhoek")).strftime("%Y-%m-%d %H:%M:%S")
        errand_id = generate_errand_id()
        otp = generate_otp()

        sheet.append_row([timestamp, errand_id, pickup, dropoff, sender, receiver, otp])

        await update.message.reply_text(
            f"✅ Errand logged successfully!\n\n"
            f"🆔 Errand ID: {errand_id}\n"
            f"📍 Pickup: {pickup}\n"
            f"📦 Dropoff: {dropoff}\n"
            f"👤 Sender: {sender}\n"
            f"📬 Receiver: {receiver}\n"
            f"🔐 OTP: {otp}",
            parse_mode="Markdown"
        )

        print(f"[LOG] {timestamp} | {errand_id} | {pickup} → {dropoff} | OTP: {otp}")

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ======== Telegram Bot Runner ========
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newerrand", new_errand))
    print("✅ Telegram Bot is now polling for updates...")
    await app.run_polling()

# ======== Main Entrypoint ========
if __name__ == "__main__":
    import asyncio

    # Run Flask in background thread
    threading.Thread(target=run_flask).start()

    # Run Telegram Bot in main thread
    asyncio.run(run_bot())

