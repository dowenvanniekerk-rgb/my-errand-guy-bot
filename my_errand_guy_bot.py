import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import pytz
from datetime import datetime


# --- Load environment variables ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SHEET_NAME = os.environ.get("SHEET_NAME", "Sheet1")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON")
LOCAL_TZ = pytz.timezone(os.environ.get("TIMEZONE", "Africa/Windhoek"))


# --- Safety checks ---
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing! Check your Render environment variables.")
if not SERVICE_ACCOUNT_JSON:
    raise ValueError("❌ SERVICE_ACCOUNT_JSON is missing! Check your Render environment variables.")


# --- Google Sheets setup ---
creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1


# --- Bot commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to My Errand Guy Bot!\nSend /newerrand to log a new request.")


async def new_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("Usage: /newerrand <pickup> <dropoff> <sender> <receiver>")
            return

        pickup, dropoff, sender, receiver = args[:4]
        now = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

        sheet.append_row([now, pickup, dropoff, sender, receiver])

        await update.message.reply_text(f"✅ New errand logged:\n📍Pickup: {pickup}\n📦Dropoff: {dropoff}\n👤Sender: {sender}\n📬Receiver: {receiver}")

    except Exception as e:
        await update.message.reply_text(f"⚠ Error logging errand: {e}")


# --- Main entry ---
async def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newerrand", new_errand))

    print("✅ Bot is running on Render and listening for Telegram updates...")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

