import os
import json
import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime
import pytz

# ==============================
# CONFIG
# ==============================
BOT_TOKEN = os.environ.get("8291555868:AAEoHFlEDm6hNg5PD4AUm7Y5hO-8aiIQQeU")
SHEET_NAME = os.environ.get("SHEET_NAME")
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON")
LOCAL_TZ = os.environ.get("TIMEZONE", "Africa/Windhoek")

# ==============================
# GOOGLE SHEET SETUP
# ==============================
creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
creds = Credentials.from_service_account_info(creds_dict, scopes=[
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# ==============================
# COMMAND HANDLERS
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Use /newerrand <Requester> <Receiver> <Pickup> <Dropoff> to log a new errand.")

async def new_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("❌ Usage: /newerrand <Requester> <Receiver> <Pickup> <Dropoff>")
            return

        requester, receiver, pickup, dropoff = args[0], args[1], args[2], args[3]
        now = datetime.now(pytz.timezone(LOCAL_TZ)).strftime("%Y-%m-%d %H:%M:%S")

        new_row = [now, requester, receiver, pickup, dropoff, "Pending"]
        sheet.append_row(new_row)
        await update.message.reply_text("✅ Errand logged successfully!")

    except Exception as e:
        await update.message.reply_text(f"⚠ Error: {e}")

# ==============================
# MAIN
# ==============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newerrand", new_errand))

    print("🚀 Bot started and running on Render...")
    app.run_polling()

if __name__ == "__main__":
    main()

