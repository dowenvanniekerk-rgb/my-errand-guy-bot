# =====================================================
#  My Errand Guy Bot v3.0
#  Full Ops Suite:
#   - /newerrand
#   - /assign
#   - /update
#   - /complete
#   - /cancel
#   - /pay
#   - /unpay
#   - /summary (today only)
#   - /help
#   - OTP verification via "Errand #1234 OTP 9999"
#
#  Sheet columns (must match EXACTLY, row 1):
#  A: Errand ID
#  B: Requester Name
#  C: Receiver Name
#  D: Pickup
#  E: Drop-off
#  F: Status
#  G: OTP
#  H: Driver
#  I: Timestamp
#  J: Paid (Y/N)
#
#  Brand voice:
#    "My Errand Guy — we run so you don't have to 🧡"
# =====================================================

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import random, datetime, gspread
from google.oauth2.service_account import Credentials

# ---------- CONFIG ----------
BOT_TOKEN = "8291555868:AAEoHFlEDm6hNg5PD4AUm7Y5hO-8aiIQQeU"
SHEET_NAME = "Errand Log"
CREDENTIALS_FILE = "credentials.json"

# ---------- GOOGLE SHEETS SETUP ----------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # "Sheet1" tab assumed

# column indexes for clarity
COL_ERRAND_ID = 1      # A
COL_REQUESTER = 2      # B
COL_RECEIVER = 3       # C
COL_PICKUP = 4         # D
COL_DROPOFF = 5        # E
COL_STATUS = 6         # F
COL_OTP = 7            # G
COL_DRIVER = 8         # H
COL_TIMESTAMP = 9      # I
COL_PAID = 10          # J

# ---------- HELPERS ----------
def get_all_records_with_rows():
    """Return list of (row_number, row_dict) for all rows that have data."""
    records = sheet.get_all_records()
    out = []
    # records[0] corresponds to row 2
    for i, row in enumerate(records, start=2):
        out.append((i, row))
    return out

def find_errand_row(errand_id: str):
    """
    Find the Google Sheets row number for a given errand id (string, no '#').
    Returns row number (int) or None.
    """
    rows = get_all_records_with_rows()
    for row_num, data in rows:
        if data.get('Errand ID') == f"#{errand_id}":
            return row_num
    return None

def now_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def today_date_str():
    # for summary grouping by date only
    return datetime.datetime.now().strftime("%Y-%m-%d")

async def reply_branded(update: Update, text: str):
    """Helper to send Markdown-formatted branded replies."""
    await update.message.reply_text(text, parse_mode="Markdown")

# ---------- /start and /help ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_branded(update,
        "👋 Hey! I'm My Errand Guy Bot.\n\n"
        "Use me to register, track, and close errands.\n\n"
        "🏁 /newerrand Requester Receiver Pickup Dropoff\n"
        "👤 /assign <id> <driver>\n"
        "🔄 /update <id> <status>\n"
        "✅ /complete <id>\n"
        "❌ /cancel <id>\n"
        "💰 /pay <id>\n"
        "💸 /unpay <id>\n"
        "📊 /summary\n"
        "ℹ /help\n\n"
        "Delivery confirmations:\n"
        "Driver sends Errand #1234 OTP 9999 to confirm handover.\n\n"
        "We run so you don’t have to 🧡"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_branded(update,
        "📖 My Errand Guy — Command Help\n\n"
        "🏁 Create new errand:\n"
        "/newerrand Requester Receiver Pickup Dropoff\n"
        "Use _ instead of spaces in names/locations.\n"
        "Example:\n"
        "/newerrand Olivia Paul Home_Affairs French_Embassy\n\n"
        "👤 Assign driver:\n"
        "/assign 6199 Heino\n\n"
        "🔄 Update status:\n"
        "/update 6199 In_Progress\n"
        "/update 6199 Pending\n"
        "/update 6199 En_Route\n"
        "/update 6199 Delivered\n\n"
        "✅ Mark complete (delivered):\n"
        "/complete 6199\n"
        "Automatically stamps time + sets Status to Delivered.\n\n"
        "❌ Cancel errand:\n"
        "/cancel 6199\n\n"
        "💰 Mark paid / unpaid:\n"
        "/pay 6199\n"
        "/unpay 6199\n\n"
        "📊 Daily summary (today only):\n"
        "/summary\n\n"
        "🚚 Driver delivery confirmation:\n"
        "Errand #6199 OTP 1234\n"
        "— marks Delivered if OTP matches.\n\n"
        "We run so you don’t have to 🧡"
    )

# ---------- /newerrand ----------
async def new_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /newerrand Requester Receiver Pickup Dropoff
    try:
        requester, receiver, pickup, dropoff = context.args[0:4]
    except:
        await reply_branded(update,
            "Usage:\n"
            "/newerrand Requester Receiver Pickup Dropoff\n"
            "Example:\n"
            "/newerrand Olivia Paul Home_Affairs French_Embassy"
        )
        return

    # Generate errand id + OTP
    errand_id = str(random.randint(1000, 9999))
    otp = str(random.randint(1000, 9999))
    timestamp = now_timestamp()

    # Append to sheet
    sheet.append_row([
        f"#{errand_id}",
        requester,
        receiver,
        pickup,
        dropoff,
        "Pending",
        otp,
        update.effective_user.first_name,
        timestamp,
        "No"
    ])

    await reply_branded(update,
        "🏁 New Errand Logged!\n"
        f"Errand #{errand_id} created.\n"
        f"Pickup: {pickup.replace('',' ')} → Drop-off: {dropoff.replace('',' ')}\n"
        f"Requester: {requester.replace('',' ')} | Receiver: {receiver.replace('',' ')}\n"
        f"🔐 OTP for receiver: {otp}\n\n"
        "Your job is in the system.\n"
        "My Errand Guy is on the move 🏃‍♂💨"
    )

# ---------- /assign ----------
async def assign_driver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /assign <id> <driver>
    try:
        errand_id, driver_name = context.args[0], context.args[1]
    except:
        await reply_branded(update, "Usage:\n`/assign <id> <driver>\nExample:\n/assign 6199 Heino`")
        return

    row = find_errand_row(errand_id)
    if not row:
        await reply_branded(update,
            f"⚠ Oops! I couldn't find Errand #{errand_id}.\n"
            "Please double-check the ID and try again."
        )
        return

    sheet.update_cell(row, COL_DRIVER, driver_name)

    await reply_branded(update,
        "🚗 Driver Assigned\n"
        f"Driver {driver_name} is now assigned to Errand #{errand_id}.\n"
        "They’re gearing up to get it done 💪"
    )

# ---------- /update ----------
async def update_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /update <id> <status>
    try:
        errand_id, new_status = context.args[0], context.args[1]
    except:
        await reply_branded(update,
            "Usage:\n`/update <id> <status>\nExample:\n/update 6199 In_Progress`"
        )
        return

    row = find_errand_row(errand_id)
    if not row:
        await reply_branded(update,
            f"⚠ Oops! I couldn't find Errand #{errand_id}.\n"
            "Please double-check the ID and try again."
        )
        return

    status_clean = new_status.replace('_', ' ')
    sheet.update_cell(row, COL_STATUS, status_clean)

    await reply_branded(update,
        "🔄 Status Update\n"
        f"Errand #{errand_id} is now *{status_clean}*.\n"
        "We're already on the move! 🏃‍♂💨"
    )

# ---------- /complete ----------
async def complete_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /complete <id>
    try:
        errand_id = context.args[0]
    except:
        await reply_branded(update,
            "Usage:\n`/complete <id>\nExample:\n/complete 6199`"
        )
        return

    row = find_errand_row(errand_id)
    if not row:
        await reply_branded(update,
            f"⚠ Hmm... Errand #{errand_id} not found.\n"
            "Please check the ID."
        )
        return

    # Mark Status = Delivered, Timestamp = now
    sheet.update_cell(row, COL_STATUS, "Delivered")
    sheet.update_cell(row, COL_TIMESTAMP, now_timestamp())

    await reply_branded(update,
        "✅ Delivery Complete!\n"
        f"Errand #{errand_id} is marked as Delivered.\n"
        "Timestamp captured. Great work team 📦💨"
    )

# ---------- /cancel ----------
async def cancel_errand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /cancel <id>
    try:
        errand_id = context.args[0]
    except:
        await reply_branded(update,
            "Usage:\n`/cancel <id>\nExample:\n/cancel 6199`"
        )
        return

    row = find_errand_row(errand_id)
    if not row:
        await reply_branded(update,
            f"⚠ Couldn't find Errand #{errand_id}.\n"
            "Check the ID and try again."
        )
        return

    sheet.update_cell(row, COL_STATUS, "Canceled")
    sheet.update_cell(row, COL_TIMESTAMP, now_timestamp())

    await reply_branded(update,
        "❌ Errand Canceled\n"
        f"Errand #{errand_id} is now marked as Canceled.\n"
        "We'll be ready when you are 💪"
    )

# ---------- /pay ----------
async def mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /pay <id>
    try:
        errand_id = context.args[0]
    except:
        await reply_branded(update,
            "Usage:\n`/pay <id>\nExample:\n/pay 6199`"
        )
        return

    row = find_errand_row(errand_id)
    if not row:
        await reply_branded(update,
            f"⚠ Couldn't find Errand #{errand_id}. Check the ID."
        )
        return

    sheet.update_cell(row, COL_PAID, "Yes")

    await reply_branded(update,
        "💰 Payment Confirmed!\n"
        f"Errand #{errand_id} marked as Paid.\n"
        "Thank you for using My Errand Guy — we run so you don’t have to 🧡"
    )

# ---------- /unpay ----------
async def mark_unpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /unpay <id>
    try:
        errand_id = context.args[0]
    except:
        await reply_branded(update,
            "Usage:\n`/unpay <id>\nExample:\n/unpay 6199`"
        )
        return

    row = find_errand_row(errand_id)
    if not row:
        await reply_branded(update,
            f"⚠ Couldn't find Errand #{errand_id}. Check the ID."
        )
        return

    sheet.update_cell(row, COL_PAID, "No")

    await reply_branded(update,
        "💸 Payment Reverted\n"
        f"Errand #{errand_id} marked as Unpaid.\n"
        "Please review outstanding balance ⚠"
    )

# ---------- /summary ----------
async def summary_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Build summary for today only based on Timestamp date
    rows = get_all_records_with_rows()
    today = today_date_str()

    total_pending = 0
    total_in_progress = 0
    total_delivered = 0
    total_canceled = 0

    paid_yes = 0
    paid_no = 0

    for row_num, data in rows:
        ts = str(data.get('Timestamp', ''))
        # check if ts starts with today's YYYY-MM-DD
        if not ts.startswith(today):
            continue

        status = data.get('Status', '').strip().lower()
        paid = data.get('Paid (Y/N)', '').strip().lower()

        if status == "pending":
            total_pending += 1
        elif "progress" in status or "route" in status or "in progress" in status:
            total_in_progress += 1
        elif status == "delivered":
            total_delivered += 1
        elif status == "canceled" or status == "cancelled":
            total_canceled += 1

        if paid == "yes":
            paid_yes += 1
        elif paid == "no":
            paid_no += 1

    msg = (
        "📊 Today’s Summary\n"
        f"Date: {today}\n\n"
        f"⏳ Pending: {total_pending}\n"
        f"🔄 In Progress: {total_in_progress}\n"
        f"✅ Delivered: {total_delivered}\n"
        f"❌ Canceled: {total_canceled}\n\n"
        f"💰 Paid: {paid_yes}\n"
        f"💸 Unpaid: {paid_no}\n\n"
        "Keep running strong, team 💨"
    )

    await reply_branded(update, msg)

# ---------- OTP VERIFICATION FROM DRIVER ----------
async def verify_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Driver sends text like:
    "Errand #1234 OTP 5678"

    -> We find errand #1234
    -> Match stored OTP
    -> If match, mark Delivered + timestamp
    -> Reply branded
    """
    text = update.message.text
    # Very lightweight pattern check
    if "Errand" in text and "OTP" in text and "#" in text:
        try:
            # Extract errand id
            after_hash = text.split("#", 1)[1]      # "1234 OTP 5678"
            errand_id_part = after_hash.split()[0]  # "1234"
            otp_given = text.split("OTP", 1)[1].strip().split()[0]  # "5678"
        except:
            return  # ignore if badly formatted

        row = find_errand_row(errand_id_part)
        if not row:
            await reply_branded(update,
                f"⚠ I couldn't find Errand #{errand_id_part}. Check the ID and try again."
            )
            return

        # Get stored OTP + Status
        cell_otp = sheet.cell(row, COL_OTP).value
        cell_status = sheet.cell(row, COL_STATUS).value

        if cell_otp == otp_given and cell_status != "Delivered":
            # Mark delivered + timestamp
            sheet.update_cell(row, COL_STATUS, "Delivered")
            sheet.update_cell(row, COL_TIMESTAMP, now_timestamp())

            await reply_branded(update,
                "📦 Delivery Confirmed!\n"
                f"Errand #{errand_id_part} is now Delivered.\n"
                "Great job team 🙌"
            )
        else:
            await reply_branded(update,
                f"⚠ OTP didn't match for Errand #{errand_id_part}.\n"
                "Please double-check with the receiver."
            )

# ---------- RUN THE BOT ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_cmd))
app.add_handler(CommandHandler("newerrand", new_errand))
app.add_handler(CommandHandler("assign", assign_driver))
app.add_handler(CommandHandler("update", update_status))
app.add_handler(CommandHandler("complete", complete_errand))
app.add_handler(CommandHandler("cancel", cancel_errand))
app.add_handler(CommandHandler("pay", mark_paid))
app.add_handler(CommandHandler("unpay", mark_unpaid))
app.add_handler(CommandHandler("summary", summary_today))

# any non-command text (like "Errand #1234 OTP 5678") goes to OTP verification
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, verify_otp))

app.run_polling()