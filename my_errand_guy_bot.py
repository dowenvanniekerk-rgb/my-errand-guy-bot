import os
import json
import random
import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram.ext import Updater, CommandHandler
from telegram import ParseMode

# =========================
# CONFIG / GLOBALS
# =========================

# Env vars from Render dashboard
BOT_TOKEN = os.environ.get("8291555868:AAEoHFlEDm6hNg5PD4AUm7Y5hO-8aiIQQeU")              # e.g. 8291:AA....
SHEET_NAME = os.environ.get("SHEET_NAME")            # e.g. MyErrandGuy
SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON")  # full JSON of google creds
LOCAL_TZ = os.environ.get("TIMEZONE", "Africa/Windhoek")

# Google Sheets columns (1-based index)
COL_ID = 1
COL_REQUESTER = 2
COL_RECEIVER = 3
COL_PICKUP = 4
COL_DROPOFF = 5
COL_STATUS = 6
COL_OTP = 7
COL_DRIVER = 8
COL_TIMESTAMP = 9
COL_PAID = 10

# -------------------------
# build Google Sheets client
# -------------------------

def build_sheet_client():
    # Write service account json from env into a temp file, so gspread can read it
    creds_dict = json.loads(SERVICE_ACCOUNT_JSON)
    tmp_path = "/tmp/service_account.json"
    with open(tmp_path, "w") as f:
        json.dump(creds_dict, f)

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(tmp_path, scope)
    gc = gspread.authorize(creds)

    # open workbook
    sh = gc.open(SHEET_NAME)
    # first sheet/tab
    ws = sh.sheet1
    return ws

sheet = build_sheet_client()

# =========================
# UTILITIES
# =========================

def now_local_str():
    tz = pytz.timezone(LOCAL_TZ)
    return datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

def today_local_date():
    tz = pytz.timezone(LOCAL_TZ)
    return datetime.datetime.now(tz).strftime("%Y-%m-%d")

def generate_errand_id():
    # Example: EG-20251102-8421  (EG + date + random 4 digits)
    tz = pytz.timezone(LOCAL_TZ)
    now = datetime.datetime.now(tz)
    date_part = now.strftime("%Y%m%d")
    rnd = random.randint(1000, 9999)
    return f"EG-{date_part}-{rnd}"

def generate_otp():
    return str(random.randint(1000, 9999))

def append_errand_row(errand_id, requester, receiver, pickup, dropoff, otp):
    timestamp = now_local_str()
    status = "Pending"
    driver = ""
    paid = "N"
    row = [
        errand_id,
        requester,
        receiver,
        pickup,
        dropoff,
        status,
        otp,
        driver,
        timestamp,
        paid,
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")

def find_row_by_errand_id(eid):
    """
    Returns (row_index, row_values) or (None, None)
    row_index is the actual sheet row number (1-based in Google Sheets)
    """
    all_ids = sheet.col_values(COL_ID)
    # first row is likely headers on row 1, so start at row 2
    for idx in range(2, len(all_ids) + 1):
        if all_ids[idx - 1] == eid:
            return idx, sheet.row_values(idx)
    return None, None

def update_cell(row_idx, col_idx, value):
    sheet.update_cell(row_idx, col_idx, value)

def update_errand_status(eid, new_status):
    row_idx, row_vals = find_row_by_errand_id(eid)
    if not row_idx:
        return False
    update_cell(row_idx, COL_STATUS, new_status)
    # if marking Delivered / Complete we also stamp new timestamp
    if new_status.lower() in ["delivered", "complete", "completed"]:
        update_cell(row_idx, COL_TIMESTAMP, now_local_str())
    return True

def assign_driver(eid, driver_name):
    row_idx, _ = find_row_by_errand_id(eid)
    if not row_idx:
        return False
    update_cell(row_idx, COL_DRIVER, driver_name)
    # if status was Pending, bump to "In Progress"
    current_status = sheet.cell(row_idx, COL_STATUS).value
    if current_status.lower() == "pending":
        update_cell(row_idx, COL_STATUS, "In Progress")
    return True

def mark_paid(eid, paid_value):
    # paid_value should be "Y" or "N"
    row_idx, _ = find_row_by_errand_id(eid)
    if not row_idx:
        return False
    update_cell(row_idx, COL_PAID, paid_value)
    return True

def get_today_summary():
    # read all rows
    all_rows = sheet.get_all_values()
    # skip header row
    body_rows = all_rows[1:]

    today_str = today_local_date()

    pending = 0
    in_progress = 0
    delivered = 0
    canceled = 0

    paid = 0
    unpaid = 0

    for r in body_rows:
        # r = [ID, Requester, Receiver, Pickup, Dropoff, Status, OTP, Driver, Timestamp, Paid]
        if len(r) < 10:
            continue

        timestamp = r[COL_TIMESTAMP - 1]  # string "YYYY-mm-dd HH:MM:SS"
        status = r[COL_STATUS - 1].strip() if r[COL_STATUS - 1] else ""
        paid_flag = r[COL_PAID - 1].strip().upper() if r[COL_PAID - 1] else ""

        # only count if job happened today
        # we match date part of timestamp == today_str
        if timestamp.startswith(today_str):
            if status.lower() == "pending":
                pending += 1
            elif status.lower() in ["in progress", "in_progress", "inprogress"]:
                in_progress += 1
            elif status.lower() in ["delivered", "complete", "completed"]:
                delivered += 1
            elif status.lower() in ["canceled", "cancelled"]:
                canceled += 1

            if paid_flag == "Y":
                paid += 1
            else:
                unpaid += 1

    msg = (
        f"📊 Today’s Summary\n"
        f"Date: {today_str}\n\n"
        f"⏳ Pending: {pending}\n"
        f"🔄 In Progress: {in_progress}\n"
        f"✅ Delivered: {delivered}\n"
        f"❌ Canceled: {canceled}\n\n"
        f"💰 Paid: {paid}\n"
        f"💸 Unpaid: {unpaid}\n\n"
        f"Keep running strong, team 💨"
    )
    return msg

# =========================
# COMMAND HANDLERS
# =========================

def help_cmd(update, context):
    text = (
        "👋 Hey! I'm My Errand Guy Bot.\n\n"
        "Use me to register, track, and close errands.\n\n"
        "🏁 /newerrand <requester> <receiver> <pickup> <dropoff>\n"
        "👤 /assign <errand_id> <driver>\n"
        "🔄 /update <errand_id> <status>\n"
        "✅ /complete <errand_id>\n"
        "❌ /cancel <errand_id>\n"
        "💰 /pay <errand_id>\n"
        "💸 /unpay <errand_id>\n"
        "📊 /summary\n"
        "ℹ /help\n\n"
        "Delivery confirmations:\n"
        "Driver sends:  Errand #1234 OTP 9999\n\n"
        "We run so you don’t have to 🧡"
    )
    update.message.reply_text(text)

def parse_newerrand_args(args_text):
    """
    We support two styles:
    1) /newerrand John Mary PickupLocation DropoffLocation
    2) /newerrand Requester: John Receiver: Mary Pickup: XYZ Dropoff: ABC
    We'll try smart extraction.
    """
    # First try style 1 (simple split)
    parts = args_text.strip().split()
    if len(parts) >= 4 and "Requester:" not in args_text and "Receiver:" not in args_text:
        requester = parts[0]
        receiver = parts[1]
        pickup = parts[2]
        dropoff = " ".join(parts[3:])
        return requester, receiver, pickup, dropoff

    # Fallback: labeled format
    # We'll just do dumb scanning
    requester = ""
    receiver = ""
    pickup = ""
    dropoff = ""

    tokens = args_text.replace("\n", " ").split()
    current_label = None
    buckets = {"requester": [], "receiver": [], "pickup": [], "dropoff": []}

    for t in tokens:
        low = t.lower().rstrip(":")
        if low in ["requester", "receiver", "pickup", "dropoff", "drop-off"]:
            current_label = "dropoff" if "drop" in low else low
            continue
        if current_label:
            buckets[current_label].append(t)

    requester = " ".join(buckets["requester"]).strip()
    receiver = " ".join(buckets["receiver"]).strip()
    pickup = " ".join(buckets["pickup"]).strip()
    dropoff = " ".join(buckets["dropoff"]).strip()

    if requester and receiver and pickup and dropoff:
        return requester, receiver, pickup, dropoff

    return None, None, None, None

def newerrand_cmd(update, context):
    # everything after /newerrand
    args_text = update.message.text.replace("/newerrand", "", 1).strip()

    requester, receiver, pickup, dropoff = parse_newerrand_args(args_text)

    if not requester or not receiver or not pickup or not dropoff:
        usage = (
            "Usage:\n"
            "/newerrand Requester Receiver Pickup Dropoff\n"
            "Example:\n"
            "/newerrand Martha Paul HomeAffairs FrenchEmbassy\n\n"
            "Or labeled:\n"
            "/newerrand Requester: Martha Receiver: Paul Pickup: Home Affairs Dropoff: French Embassy"
        )
        update.message.reply_text(usage)
        return

    # create id + otp
    eid = generate_errand_id()
    otp = generate_otp()

    # save row in sheet
    append_errand_row(eid, requester, receiver, pickup, dropoff, otp)

    # reply
    reply = (
        f"🏁 New Errand Logged!\n"
        f"Errand {eid} created.\n"
        f"Pickup: {pickup} → Drop-off: {dropoff}\n"
        f"Requester: {requester} | Receiver: {receiver}\n"
        f"🔐 OTP for receiver: {otp}\n\n"
        f"Your job is in the system.\n"
        f"My Errand Guy is on the move 🏃‍♂💨"
    )
    update.message.reply_text(reply)

def assign_cmd(update, context):
    # /assign <errand_id> <driver>
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        update.message.reply_text("Usage:\n/assign <errand_id> <driver>")
        return
    _, eid, driver_name = parts[0], parts[1], " ".join(parts[2:])
    ok = assign_driver(eid, driver_name)
    if not ok:
        update.message.reply_text(f"Could not find {eid}.")
        return
    reply = (
        f"🚗 Driver Assigned\n"
        f"Driver {driver_name} is now assigned to {eid}.\n"
        f"They’re gearing up to get it done 💪"
    )
    update.message.reply_text(reply)

def update_cmd(update, context):
    # /update <errand_id> <status>
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        update.message.reply_text("Usage:\n/update <errand_id> <status>\nExample:\n/update EG-20251102-1234 In_Progress")
        return
    _, eid, new_status = parts[0], parts[1], " ".join(parts[2:])
    ok = update_errand_status(eid, new_status)
    if not ok:
        update.message.reply_text(f"Could not find {eid}.")
        return
    reply = (
        f"🔄 Status Update\n"
        f"{eid} is now {new_status}.\n"
        f"We're already on the move! 🏃‍♂💨"
    )
    update.message.reply_text(reply)

def complete_cmd(update, context):
    # /complete <errand_id>
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        update.message.reply_text("Usage:\n/complete <errand_id>")
        return
    eid = parts[1]
    ok = update_errand_status(eid, "Delivered")
    if not ok:
        update.message.reply_text(f"Could not find {eid}.")
        return
    reply = (
        f"✅ Delivery Complete!\n"
        f"{eid} is marked as Delivered.\n"
        f"Timestamp captured. Great work team 📦💨"
    )
    update.message.reply_text(reply)

def cancel_cmd(update, context):
    # /cancel <errand_id>
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        update.message.reply_text("Usage:\n/cancel <errand_id>")
        return
    eid = parts[1]
    ok = update_errand_status(eid, "Canceled")
    if not ok:
        update.message.reply_text(f"Could not find {eid}.")
        return
    reply = (
        f"❌ Errand Canceled\n"
        f"{eid} is now canceled."
    )
    update.message.reply_text(reply)

def pay_cmd(update, context):
    # /pay <errand_id>
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        update.message.reply_text("Usage:\n/pay <errand_id>")
        return
    eid = parts[1]
    ok = mark_paid(eid, "Y")
    if not ok:
        update.message.reply_text(f"Could not find {eid}.")
        return
    reply = (
        f"💰 Payment Confirmed!\n"
        f"{eid} marked as Paid.\n"
        f"Thank you for using My Errand Guy — we run so you don’t have to 🧡"
    )
    update.message.reply_text(reply)

def unpay_cmd(update, context):
    # /unpay <errand_id>
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        update.message.reply_text("Usage:\n/unpay <errand_id>")
        return
    eid = parts[1]
    ok = mark_paid(eid, "N")
    if not ok:
        update.message.reply_text(f"Could not find {eid}.")
        return
    reply = (
        f"💸 Payment Reverted\n"
        f"{eid} marked as Unpaid."
    )
    update.message.reply_text(reply)

def summary_cmd(update, context):
    msg = get_today_summary()
    update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

def start_cmd(update, context):
    # simple sanity /start
    update.message.reply_text("My Errand Guy Bot is live and ready 🏃‍♂💨 Use /help for commands.")

# =========================
# BOOTSTRAP BOT
# =========================

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_cmd))
    dp.add_handler(CommandHandler("help", help_cmd))
    dp.add_handler(CommandHandler("newerrand", newerrand_cmd))
    dp.add_handler(CommandHandler("assign", assign_cmd))
    dp.add_handler(CommandHandler("update", update_cmd))
    dp.add_handler(CommandHandler("complete", complete_cmd))
    dp.add_handler(CommandHandler("cancel", cancel_cmd))
    dp.add_handler(CommandHandler("pay", pay_cmd))
    dp.add_handler(CommandHandler("unpay", unpay_cmd))
    dp.add_handler(CommandHandler("summary", summary_cmd))

    print("✅ Bot started... Listening for new errands...")
    updater.start_polling()
    updater.idle()

if _name_ == "_main_":
    main()
