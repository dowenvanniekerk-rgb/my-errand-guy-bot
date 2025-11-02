import os
import json
import random
import string
import datetime
import asyncio
from flask import Flask
from threading import Thread

import gspread
from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials  # still used by gspread sometimes
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# =========================
# 1. ENVIRONMENT VARIABLES
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # from BotFather
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")  # full JSON from Google service account
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "MyErrandGuy_DB")  # you chose this in Render

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it in Render env vars.")

if not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("SERVICE_ACCOUNT_JSON is missing. Set it in Render env vars.")

# ==========================================
# 2. GOOGLE SHEETS AUTH + SHEET PREP LOGIC
# ==========================================

REQUIRED_COLUMNS = [
    "ErrandID",
    "OTP",
    "Pickup",
    "Dropoff",
    "SenderName",
    "SenderPhone",
    "ReceiverName",
    "ReceiverPhone",
    "Status",
]

def get_google_client_and_sheet():
    """
    1. Auth to Google using the service account JSON string from env.
    2. Ensure spreadsheet exists.
    3. Ensure header row exists.
    4. Return the worksheet object.
    """
    creds_dict = json.loads(SERVICE_ACCOUNT_JSON)

    # gspread wants google.oauth2.service_account creds normally:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

    client = gspread.authorize(creds)

    # Try open spreadsheet by name; if not exists, create it
    try:
        sh = client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SPREADSHEET_NAME)

        # IMPORTANT:
        # Share the sheet with the service account email so it can edit.
        # Some service accounts auto-own created sheets so it's already fine.

    # Use first worksheet
    try:
        ws = sh.sheet1
    except Exception:
        ws = sh.add_worksheet(title="Sheet1", rows="100", cols="20")

    # Make sure header row is correct
    current_header = ws.row_values(1)
    if current_header != REQUIRED_COLUMNS:
        # rewrite row 1 with required headers
        ws.clear()
        ws.append_row(REQUIRED_COLUMNS)

    return ws


# ==================================================
# 3. SMALL HELPERS: ID GEN, OTP GEN, LIST FORMATTING
# ==================================================

def generate_errand_id():
    # Example: ERR-20251102-3841
    today = datetime.datetime.now().strftime("%Y%m%d")
    rand_part = ''.join(random.choices(string.digits, k=4))
    return f"ERR-{today}-{rand_part}"

def generate_otp():
    # 4 digit numeric
    return ''.join(random.choices(string.digits, k=4))

def format_errand_for_reply(row_dict):
    """
    row_dict keys: see REQUIRED_COLUMNS
    """
    status = row_dict.get("Status", "Pending")
    return (
        f"🆔 <b>{row_dict['ErrandID']}</b>\n"
        f"📦 <b>Pickup:</b> {row_dict['Pickup']}\n"
        f"🎯 <b>Dropoff:</b> {row_dict['Dropoff']}\n"
        f"👤 <b>Sender:</b> {row_dict['SenderName']} ({row_dict['SenderPhone']})\n"
        f"📞 <b>Receiver:</b> {row_dict['ReceiverName']} ({row_dict['ReceiverPhone']})\n"
        f"🔐 <b>OTP:</b> {row_dict['OTP']}\n"
        f"📌 <b>Status:</b> {status}\n"
        f"— — — — —"
    )

def get_all_rows_as_dicts(ws):
    """
    Returns a list of dicts with keys from REQUIRED_COLUMNS.
    """
    records = ws.get_all_records()  # list of dicts, using row1 headers
    return records


# ========================================
# 4. TELEGRAM COMMAND HANDLERS
# ========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 Welcome to My Errand Guy.\n\n"
        "Use commands:\n"
        "/newerrand <pickup> | <dropoff> | <sender_name> | <sender_phone> | <receiver_name> | <receiver_phone>\n"
        "→ I'll generate an Errand ID + OTP and save it.\n\n"
        "/list\n"
        "→ See all errands that are still NOT completed.\n\n"
        "/verify <ErrandID> <OTP>\n"
        "→ Mark an errand completed (use at drop-off once receiver gives OTP).\n"
    )
    await update.message.reply_text(msg)

async def newerrand_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /newerrand Maerua Mall | Rehoboth Caltex | John | 0811111111 | Mary | 0812222222
    """
    ws = get_google_client_and_sheet()

    # join all args back into one string
    raw_text = " ".join(context.args)

    # split by | into exactly 6 parts
    parts = [p.strip() for p in raw_text.split("|")]
    if len(parts) != 6:
        usage = (
            "❌ Format error.\n"
            "Correct usage:\n"
            "/newerrand pickup | dropoff | sender_name | sender_phone | receiver_name | receiver_phone"
        )
        await update.message.reply_text(usage)
        return

    pickup, dropoff, s_name, s_phone, r_name, r_phone = parts

    errand_id = generate_errand_id()
    otp = generate_otp()

    # Append row to sheet
    new_row = [
        errand_id,
        otp,
        pickup,
        dropoff,
        s_name,
        s_phone,
        r_name,
        r_phone,
        "Pending",
    ]
    ws.append_row(new_row)

    reply = (
        f"✅ New Errand Created\n"
        f"🆔 ErrandID: <b>{errand_id}</b>\n"
        f"🔐 OTP: <b>{otp}</b>\n\n"
        f"📦 Pickup: {pickup}\n"
        f"🎯 Dropoff: {dropoff}\n"
        f"👤 Sender: {s_name} ({s_phone})\n"
        f"📞 Receiver: {r_name} ({r_phone})\n\n"
        f"Driver instruction:\n"
        f"1. Collect parcel from sender.\n"
        f"2. Deliver to receiver.\n"
        f"3. Ask receiver for OTP {otp}.\n"
        f"4. Send /verify {errand_id} {otp} to close job."
    )

    await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ws = get_google_client_and_sheet()
    all_rows = get_all_rows_as_dicts(ws)

    # filter status not completed
    outstanding = [r for r in all_rows if str(r.get("Status", "")).lower() != "completed ✅" and str(r.get("Status", "")).lower() != "completed"]

    if not outstanding:
        await update.message.reply_text("✅ All errands are completed. Nothing pending.")
        return

    chunks = []
    for r in outstanding:
        chunks.append(format_errand_for_reply(r))

    final_msg = "📋 Outstanding errands:\n\n" + "\n\n".join(chunks)
    await update.message.reply_text(final_msg, parse_mode=ParseMode.HTML)

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /verify ERR-20251102-3841 1234
    """
    ws = get_google_client_and_sheet()

    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /verify <ErrandID> <OTP>")
        return

    given_id = context.args[0].strip()
    given_otp = context.args[1].strip()

    # pull all data including row numbers so we can update Status
    all_values = ws.get_all_values()  # list of rows (list of cells)
    # first row is header
    header = all_values[0]
    # build lookup from column name to index
    col_index = {header[i]: i for i in range(len(header))}

    # walk rows from row 2 onwards with index
    match_row_number = None
    for i in range(1, len(all_values)):
        row = all_values[i]

        row_id = row[col_index["ErrandID"]] if "ErrandID" in col_index and col_index["ErrandID"] < len(row) else ""
        row_otp = row[col_index["OTP"]] if "OTP" in col_index and col_index["OTP"] < len(row) else ""

        if row_id == given_id and row_otp == given_otp:
            match_row_number = i + 1  # because sheet rows start at 1, and we skipped header
            break

    if not match_row_number:
        await update.message.reply_text("❌ Invalid OTP or ErrandID. Try again.")
        return

    # update Status column for that row to Completed ✅
    if "Status" not in col_index:
        await update.message.reply_text("⚠ Sheet missing 'Status' column.")
        return

    status_col_number = col_index["Status"] + 1  # gspread is 1-based
    ws.update_cell(match_row_number, status_col_number, "Completed ✅")

    await update.message.reply_text(
        f"✅ Verified! Errand {given_id} is now marked Completed ✅"
    )


# ======================
# 5. FLASK KEEPALIVE
# ======================

app = Flask(_name_)

@app.route("/health")
def health():
    return "OK", 200

def run_flask():
    # Bind to whatever Render gives us or default 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ======================
# 6. MAIN APP LOOP
# ======================

async def main():
    # start telegram app
    tg_app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    tg_app.add_handler(CommandHandler("start", start_command))
    tg_app.add_handler(CommandHandler("newerrand", newerrand_command))
    tg_app.add_handler(CommandHandler("list", list_command))
    tg_app.add_handler(CommandHandler("verify", verify_command))

    # run polling forever
    await tg_app.initialize()
    await tg_app.start()
    print("🚚 My Errand Guy Bot is LIVE and polling for updates...")
    await tg_app.updater.start_polling()
    await tg_app.updater.idle()

if __name__ == "__main__":
    # start Flask in a side thread so Render sees an open port
    t = Thread(target=run_flask, daemon=True)
    t.start()

    # start telegram polling loop
    asyncio.run(main())
