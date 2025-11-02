import os
import json
import gspread
import pytz
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ───────────────────────────────
#   Environment & configuration
# ───────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
SHEET_NAME = os.getenv("SHEET_NAME", "Sheet1")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN missing — check Render Environment tab.")
if not SERVICE_ACCOUNT_JSON:
    raise ValueError("❌ SERVICE_ACCOUNT_JSON missing — check Render Environment tab.")

LOCAL_TZ = pytz.timezone(os.getenv("TIMEZONE", "Africa/Windhoek"))

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
#   Telegram command handlers
# ───────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to My Errand Guy Bot!\n"
        "Use /newerrand pickup dropoff sender receiver to log a job.",
        parse_mode="Markdown",
    )


async def new_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "Usage:\n/newerrand <pickup> <dropoff> <sender> <receiver>"
        )
        return

    pickup, dropoff, sender, receiver = args[:4]
    now = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S")

    try:
        sheet.append_row([now, pickup, dropoff, sender, receiver])
        await update.message.reply_text(
            f"✅ Logged!\n📍Pickup {pickup}\n📦Dropoff {dropoff}\n👤Sender {sender}\n📬Receiver {receiver}"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠ Failed to write to sheet:\n{e}")


# ───────────────────────────────
#   Main entrypoint
# ───────────────────────────────
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newerrand", new_errand))

    print("✅ Bot deployed successfully — now polling for messages...")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
