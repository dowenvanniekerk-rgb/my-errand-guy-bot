import os
import json
import gspread
import pytz
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ───────────────────────────────
#   Environment setup
# ───────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
TIMEZONE = os.getenv("TIMEZONE", "Africa/Windhoek")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing — check Render environment.")
if not SERVICE_ACCOUNT_JSON:
    raise ValueError("❌ SERVICE_ACCOUNT_JSON missing — check Render environment.")

LOCAL_TZ = pytz.timezone(TIMEZONE)

# ───────────────────────────────
#   Google Sheets setup
# ───────────────────────────────
creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# ───────────────────────────────
#   Command Handlers
# ───────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to My Errand Guy Bot!\n"
        "Use /newerrand pickup dropoff sender receiver to log your job.",
        parse_mode="Markdown",
    )

async def new_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 4:
        await update.message.reply_text("Usage:\n/newerrand pickup dropoff sender receiver")
        return

    pickup, dropoff, sender, receiver = args[:4]
    now = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

    try:
        sheet.append_row([now, pickup, dropoff, sender, receiver])
        await update.message.reply_text(
            f"✅ Logged successfully!\n"
            f"📍Pickup: {pickup}\n📦Dropoff: {dropoff}\n👤Sender: {sender}\n📬Receiver: {receiver}"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠ Failed to write to sheet: {e}")

# ───────────────────────────────
#   Main App
# ───────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newerrand", new_errand))

    print("✅ My Errand Guy Bot is LIVE and polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
