import os, time, threading, requests, sqlite3, telebot
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ================= CONFIGURATION =================
BOT_TOKEN = "9210228258:AAH0n4daYi886XSCL1vo-uzvu2U4rUHQOeQ"
SASTA_API_KEY = "stp_be56da49464530c208bb617d86fcedad83101bc5380ba646"
BASE_URL = "https://sastasms.pro/stubs/handler_api.php"

ADMIN_ID = 8539777823
ADMIN_USERNAME = "@ub2_q"
UPI_ID = "noname0011@axl"
REFER_COMMISSION_PERCENT = 5.0

SERVICES = {
    "tg": {"name": "Telegram", "icon": "✈️"},
    "wa": {"name": "WhatsApp", "icon": "💬"}
}

# Country Catalog with Prices (INR)
COUNTRIES = [
    {"id": "22", "name": "India", "flag": "🇮🇳", "tg": 45, "wa": 55},
    {"id": "2",  "name": "Kazakhstan", "flag": "🇰🇿", "tg": 38, "wa": 48},
    {"id": "0",  "name": "Russia", "flag": "🇷🇺", "tg": 42, "wa": 50},
    {"id": "12", "name": "USA", "flag": "🇺🇸", "tg": 50, "wa": 60},
    {"id": "3",  "name": "China", "flag": "🇨🇳", "tg": 35, "wa": 45},
    {"id": "6",  "name": "Indonesia", "flag": "🇮🇩", "tg": 40, "wa": 50},
    {"id": "10", "name": "Vietnam", "flag": "🇻🇳", "tg": 42, "wa": 52},
    {"id": "96", "name": "Zimbabwe", "flag": "🇿🇼", "tg": 40, "wa": 50},
    {"id": "63", "name": "Czech Rep.", "flag": "🇨🇿", "tg": 48, "wa": 58},
    {"id": "107","name": "S. Africa", "flag": "🇿🇦", "tg": 45, "wa": 55},
    {"id": "26", "name": "Colombia", "flag": "🇨🇴", "tg": 50, "wa": 60},
    {"id": "158","name": "Armenia", "flag": "🇦🇲", "tg": 52, "wa": 62},
    {"id": "34", "name": "Chile", "flag": "🇨🇱", "tg": 50, "wa": 60},
    {"id": "85", "name": "Moldova", "flag": "🇲🇩", "tg": 55, "wa": 65},
    {"id": "316","name": "Georgia", "flag": "🇬🇪", "tg": 60, "wa": 70},
    {"id": "464","name": "Uzbekistan", "flag": "🇺🇿", "tg": 75, "wa": 85}
]
# =================================================

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7!")

    def log_message(self, format, *args):
        return

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0, referred_by INTEGER DEFAULT 0)")
conn.commit()

user_dep_amt = {}

def get_user(uid):
    cur.execute("SELECT balance, referred_by FROM users WHERE user_id = ?", (uid,))
    r = cur.fetchone()
    if r:
        return r[0], r[1]
    cur.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 0.0, 0)", (uid,))
    conn.commit()
    return 0.0, 0

def get_bal(uid):
    bal, _ = get_user(uid)
    return bal

def update_bal(uid, amt):
    b = get_bal(uid) + amt
    cur.execute("UPDATE users SET balance = ? WHERE user_id = ?", (b, uid))
    conn.commit()
    return b

def set_referrer(uid, ref_id):
    cur.execute("SELECT referred_by FROM users WHERE user_id = ?", (uid,))
    r = cur.fetchone()
    if not r:
        cur.execute("INSERT INTO users (user_id, balance, referred_by) VALUES (?, 0.0, ?)", (uid, ref_id))
        conn.commit()
    elif r[0] == 0 and uid != ref_id:
        cur.execute("UPDATE users SET referred_by = ? WHERE user_id = ?", (ref_id, uid))
        conn.commit()

def get_service_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("✈️ Telegram OTP", callback_data="svc_tg"),
        InlineKeyboardButton("💬 WhatsApp OTP", callback_data="svc_wa")
    )
    markup.add(
        InlineKeyboardButton("💰 Wallet Balance", callback_data="menu_bal"),
        InlineKeyboardButton("➕ Add Fund (UPI)", callback_data="menu_dep")
    )
    markup.add(
        InlineKeyboardButton("👥 Refer & Earn (5%)", callback_data="menu_ref")
    )
    return markup

def get_countries_menu(service):
    markup = InlineKeyboardMarkup(row_width=2)
    btns = []
    for c in COUNTRIES:
        cid = c["id"]
        price = c[service]
        btn_text = f"{c['flag']} {c['name']} | ₹{price}"
        btns.append(InlineKeyboardButton(text=btn_text, callback_data=f"buy_{service}_{cid}_{price}"))

    for i in range(0, len(btns), 2):
        markup.row(*btns[i:i+2])

    markup.add(InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="back_main"))
    return markup

def get_deposit_menu():
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("₹20", callback_data="setdep_20"),
        InlineKeyboardButton("₹50", callback_data="setdep_50"),
        InlineKeyboardButton("₹100", callback_data="setdep_100"),
        InlineKeyboardButton("₹200", callback_data="setdep_200")
    )
    return mk

@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    name = m.from_user.first_name or "User"
    parts = m.text.split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            ref_id = int(parts[1].replace("ref_", ""))
            set_referrer(uid, ref_id)
        except:
            pass
    bal = get_bal(uid)
    text = (
        f"Namaste <b>{name}</b>!\n\n"
        f"Wallet Balance: <b>₹{bal:.2f}</b>\n"
        f"User ID: <code>{uid}</code>\n"
        f"Support: {ADMIN_USERNAME}\n\n"
        f"Neeche se apni service choose karein:"
    )
    bot.reply_to(m, text, reply_markup=get_service_menu(), parse_mode="HTML")

@bot.message_handler(commands=["stock"])
def stock_cmd(m):
    bot.reply_to(m, "Sabhi countries ka stock available hai! /start dabakar apni pasand ki country choose karein.")

@bot.message_handler(commands=["balance"])
def balance(m):
    bot.reply_to(m, f"Aapka Wallet Balance: ₹{get_bal(m.from_user.id):.2f}")

@bot.message_handler(commands=["refer"])
def refer_cmd(m):
    uid = m.from_user.id
    bu = bot.get_me().username
    ref_link = f"https://t.me/{bu}?start=ref_{uid}"
    cur.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,))
    total_refs = cur.fetchone()[0]
    text = (
        f"<b>Refer & Earn Program</b>\n\n"
        f"Apne dosto ko bot share karein. Har deposit par <b>5% Commission</b> direct wallet me payein!\n\n"
        f"Total Referrals: <b>{total_refs}</b>\n\n"
        f"Aapka Referral Link:\n<code>{ref_link}</code>"
    )
    bot.reply_to(m, text, parse_mode="HTML")

@bot.message_handler(commands=["deposit"])
def dep(m):
    bot.reply_to(m, "Amount select karein ya direct amount likh kar bhejein:", reply_markup=get_deposit_menu(), parse_mode="HTML")

@bot.message_handler(func=lambda m: not m.text.startswith("/"))
def text_flow(m):
    uid = m.from_user.id
    raw = m.text.strip()
    name = m.from_user.first_name or "User"
    if raw.isdigit():
        amt = float(raw)
        if amt < 20:
            bot.reply_to(m, "Minimum deposit ₹20 hai.")
            return
        user_dep_amt[uid] = amt
        reply = (
            f"<b>Deposit Amount: ₹{amt:.2f}</b>\n\n"
            f"UPI par pay karein: <code>{UPI_ID}</code>\n\n"
            f"Payment ke baad 12-digit UTR number ya payment Screenshot bhejein!\n\n"
            f"Support: {ADMIN_USERNAME}"
        )
        bot.reply_to(m, reply, parse_mode="HTML")
        return
    amt = user_dep_amt.get(uid, 20.0)
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton(f"Approve ₹{int(amt)}", callback_data=f"app_{uid}_{amt}"),
        InlineKeyboardButton("Reject", callback_data=f"rej_{uid}")
    )
    admin_msg = (
        f"<b>Naya UTR Deposit Request!</b>\n"
        f"User: <b>{name}</b> (<code>{uid}</code>)\n"
        f"Amount: <b>₹{amt:.2f}</b>\n"
        f"UTR: <code>{raw}</code>"
    )
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=mk, parse_mode="HTML")
    bot.reply_to(m, f"Payment proof mil gaya! 5-10 minute me check karke balance add ho jayega.\nSupport: {ADMIN_USERNAME}", parse_mode="HTML")

@bot.message_handler(content_types=['photo'])
def photo_flow(m):
    uid = m.from_user.id
    amt = user_dep_amt.get(uid, 20.0)
    cap = m.caption if m.caption else "No UTR"
    name = m.from_user.first_name or "User"
    mk = InlineKeyboardMarkup()
    mk.row(
        InlineKeyboardButton(f"Approve ₹{int(amt)}", callback_data=f"app_{uid}_{amt}"),
        InlineKeyboardButton("Reject", callback_data=f"rej_{uid}")
    )
    admin_cap = (
        f"<b>Naya Screenshot Deposit!</b>\n"
        f"User: <b>{name}</b> (<code>{uid}</code>)\n"
        f"Amount: <b>₹{amt:.2f}</b>\n"
        f"Caption: <code>{cap}</code>"
    )
    bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=admin_cap, reply_markup=mk, parse_mode="HTML")
    bot.reply_to(m, f"Screenshot mil gaya! Admin verification ke baad balance add ho jayega.\nSupport: {ADMIN_USERNAME}", parse_mode="HTML")

def poll_otp(cid, uid, activation_id, price):
    status_url = f"{BASE_URL}?api_key={SASTA_API_KEY}&action=getStatus&id={activation_id}&format=json"
    cancel_url = f"{BASE_URL}?api_key={SASTA_API_KEY}&action=setStatus&status=8&id={activation_id}"
    
    for _ in range(40):
        time.sleep(3)
        try:
            r = requests.get(status_url, timeout=5)
            try:
                res = r.json()
                if res.get("status") == "STATUS_OK" or "code" in res:
                    otp = res.get("code") or res.get("sms")
                    bot.send_message(cid, f"<b>OTP Code:</b> <code>{otp}</code>", parse_mode="HTML")
                    return
            except:
                text_res = r.text
                if "STATUS_OK" in text_res:
                    otp = text_res.split(":")[-1]
                    bot.send_message(cid, f"<b>OTP Code:</b> <code>{otp}</code>", parse_mode="HTML")
                    return
        except:
            pass

    try:
        requests.get(cancel_url, timeout=5)
    except:
        pass
    update_bal(uid, price)
    bot.send_message(cid, "Timeout: OTP nahi aaya. Order cancel karke paise wallet me wapas refund kar diye gaye hain.")

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    bal = get_bal(uid)
    if call.data == "back_main":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Wallet Balance: <b>₹{bal:.2f}</b>\nSupport: {ADMIN_USERNAME}\n\nNeeche se service choose karein:",
            reply_markup=get_service_menu(),
            parse_mode="HTML"
        )
    elif call.data.startswith("svc_"):
        service = call.data.split("_")[1]
        s_name = SERVICES.get(service, {}).get("name", "Service")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Selected: <b>{s_name}</b>\n\nNeeche se country choose karein:",
            reply_markup=get_countries_menu(service),
            parse_mode="HTML"
        )
    elif call.data == "menu_bal":
        bot.answer_callback_query(call.id, f"Aapka Balance: ₹{bal:.2f}", show_alert=True)
    elif call.data == "menu_ref":
        bu = bot.get_me().username
        cur.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (uid,))
        refs = cur.fetchone()[0]
        t = f"<b>Refer & Earn (5%)</b>\n\nLink: <code>https://t.me/{bu}?start=ref_{uid}</code>\nTotal Referrals: <b>{refs}</b>"
        bot.send_message(call.message.chat.id, t, parse_mode="HTML")
        bot.answer_callback_query(call.id)
    elif call.data == "menu_dep":
        bot.send_message(call.message.chat.id, "Deposit Amount choose karein:", reply_markup=get_deposit_menu())
        bot.answer_callback_query(call.id)
    elif call.data.startswith("setdep_"):
        a = float(call.data.split("_")[1])
        user_dep_amt[uid] = a
        reply = (
            f"<b>Deposit Amount: ₹{a:.2f}</b>\n\n"
            f"UPI par pay karein: <code>{UPI_ID}</code>\n\n"
            f"Payment ke baad 12-digit UTR ya screenshot bhejein!\n\n"
            f"Support: {ADMIN_USERNAME}"
        )
        bot.send_message(call.message.chat.id, reply, parse_mode="HTML")
        bot.answer_callback_query(call.id)
    elif call.data.startswith("app_"):
        if uid != ADMIN_ID:
            return
        _, tu, am = call.data.split("_")
        target = int(tu)
        amt = float(am)
        nb = update_bal(target, amt)
        msg = f"<b>Approved!</b> User: <code>{target}</code> | Added: ₹{amt} | Bal: ₹{nb:.2f}"
        if call.message.photo:
            bot.edit_message_caption(caption=msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")
        else:
            bot.edit_message_text(text=msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")
        try:
            bot.send_message(target, f"<b>Payment Approved!</b>\nWallet me ₹{amt:.2f} add ho gaye hain.\nCurrent Balance: ₹{nb:.2f}", parse_mode="HTML")
        except:
            pass
        _, ref_by = get_user(target)
        if ref_by and ref_by > 0:
            comm = round(amt * (REFER_COMMISSION_PERCENT / 100.0), 2)
            if comm > 0:
                rb = update_bal(ref_by, comm)
                try:
                    bot.send_message(ref_by, f"<b>Referral Commission!</b>\nReferral user ne ₹{amt} deposit kiye.\n5% Commission (+₹{comm}) mila!\nBalance: ₹{rb}", parse_mode="HTML")
                except:
                    pass
    elif call.data.startswith("rej_"):
        if uid != ADMIN_ID:
            return
        tu = int(call.data.split("_")[1])
        m = f"Rejected! User: <code>{tu}</code>"
        if call.message.photo:
            bot.edit_message_caption(caption=m, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")
        else:
            bot.edit_message_text(text=m, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML")
        try:
            bot.send_message(tu, "Payment request reject kar di gayi hai.")
        except:
            pass
    elif call.data.startswith("buy_"):
        parts = call.data.split("_")
        service = parts[1]
        code = parts[2]
        p = float(parts[3])
        s_name = SERVICES.get(service, {}).get("name", service.upper())

        if bal < p:
            bot.answer_callback_query(call.id, f"Balance kam hai! Price: ₹{int(p)}, Bal: ₹{bal:.2f}", show_alert=True)
            return

        bot.answer_callback_query(call.id, f"Ordering {s_name}...")
        bot.send_message(call.message.chat.id, f"{s_name} number manga rahe hain, thoda wait karein...")

        req_url = f"{BASE_URL}?api_key={SASTA_API_KEY}&action=getNumber&service={service}&country={code}&format=json"
        try:
            r = requests.get(req_url, timeout=10)
            res = r.json()
        except:
            bot.send_message(call.message.chat.id, "Connection error! Thodi der baad try karein.")
            return

        activation_id = res.get("activation_id") or res.get("id")
        phone = res.get("phone") or res.get("number")

        if not phone or not activation_id:
            err = res.get("error") or res.get("msg") or "Is country ka number filhal stock me nahi hai."
            bot.send_message(call.message.chat.id, f"Failed: {err}")
            return

        update_bal(uid, -p)
        bot.send_message(call.message.chat.id, f"<b>{s_name} Number:</b> <code>+{phone}</code>\nDeducted: ₹{int(p)}\nWaiting for OTP...", parse_mode="HTML")
        threading.Thread(target=poll_otp, args=(call.message.chat.id, uid, activation_id, p)).start()

print(">> BOT RUNNING WITH FULL HINGLISH SUPPORT <<")
bot.infinity_polling(skip_pending=True)
