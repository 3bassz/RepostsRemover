# Telegram TikTok Repost Remover Bot (Advanced Dashboard Version)
import os
import aiohttp
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN, OWNER_CHAT_ID

USERS_FILE = "users.json"
BLOCKED_FILE = "blocked.json"
WELCOME_FILE = "welcome.txt"
SESSIONS_DIR = "sessions"
TICKETS_FILE = "tickets.json"
SETTINGS_FILE = "settings.json"

os.makedirs(SESSIONS_DIR, exist_ok=True)
for file in [USERS_FILE, BLOCKED_FILE, TICKETS_FILE, SETTINGS_FILE]:
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False)
if not os.path.exists(WELCOME_FILE):
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        f.write("\ud83d\udd10 لحذف الريبوستات، أرسل sessionid الخاص بك:")

# ---------- Utils ----------
def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------- Menus ----------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\uddd1\ufe0f حذف الريبوستات", callback_data='delete_reposts')],
        [InlineKeyboardButton("\ud83d\udcc4 استخراج sessionid تلقائيًا", url='https://vt.tiktok.com/ZSkUaFXQf/')],
        [InlineKeyboardButton("\ud83d\udccc شرح استخراج sessionid", url='https://t.me/sessionid_extractor_bot')],
        [InlineKeyboardButton("\ud83d\udc96 دعم البوت للاستمرار", url='https://example.com/donate')],
        [InlineKeyboardButton("\ud83d\udce9 إرسال تذكرة دعم", callback_data='send_ticket')]
    ])

def back_menu(target="main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("\ud83d\udd19 رجوع", callback_data=f'back_{target}')]])

def dashboard_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\udc65 عدد المستخدمين", callback_data='user_count'), InlineKeyboardButton("\ud83d\udcc2 تصدير المستخدمين", callback_data='export_users')],
        [InlineKeyboardButton("\ud83d\udd12 تعطيل/تفعيل البوت", callback_data='toggle_bot'), InlineKeyboardButton("\ud83d\udcdd تعديل رسالة الترحيب", callback_data='edit_welcome')],
        [InlineKeyboardButton("\ud83c\udf9f\ufe0f عرض سجل التذاكر", callback_data='view_tickets'), InlineKeyboardButton("\u274c حظر مستخدم", callback_data='block_user')],
        [InlineKeyboardButton("\ud83d\udce2 إرسال رسالة جماعية", callback_data='broadcast')]
    ])

# ---------- Start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)

    settings = load_json(SETTINGS_FILE)
    if not settings.get("enabled", True) and user_id != str(OWNER_CHAT_ID):
        return

    blocked = load_json(BLOCKED_FILE)
    if user_id in blocked:
        return

    users = load_json(USERS_FILE)
    if user_id not in users:
        users[user_id] = datetime.now().isoformat()
        save_json(USERS_FILE, users)

    with open(WELCOME_FILE, "r", encoding="utf-8") as f:
        welcome_text = f.read()

    await update.message.reply_text(welcome_text, reply_markup=main_menu())

# ---------- Handlers ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(query.from_user.id)

    if data == "delete_reposts":
        context.user_data['delete_mode'] = True
        await query.edit_message_text("\ud83d\uddd1\ufe0f أرسل sessionid الآن لبدء العد والحذف.", reply_markup=back_menu("main"))

    elif data == "send_ticket":
        context.user_data['ticket_mode'] = True
        await query.edit_message_text("\u270d\ufe0f أرسل استفسارك أو مشكلتك الآن:", reply_markup=back_menu("main"))

    elif data == "dashboard_main":
        if user_id != str(OWNER_CHAT_ID):
            await query.edit_message_text("\u274c ليس لديك صلاحية الوصول.")
            return
        await query.edit_message_text("\ud83d\udcca لوحة تحكم المالك:", reply_markup=dashboard_menu())

    elif data.startswith("back_"):
        target = data.split("_", 1)[1]
        if target == "main":
            if user_id == str(OWNER_CHAT_ID):
                await query.edit_message_text("\ud83d\udcca لوحة تحكم المالك:", reply_markup=dashboard_menu())
            else:
                with open(WELCOME_FILE, "r", encoding="utf-8") as f:
                    welcome_text = f.read()
                await query.edit_message_text(welcome_text, reply_markup=main_menu())

    elif data == "user_count":
        if user_id != str(OWNER_CHAT_ID): return
        users = load_json(USERS_FILE)
        await query.edit_message_text(f"\ud83d\udc65 عدد المستخدمين: {len(users)}", reply_markup=back_menu("main"))

    elif data == "export_users":
        if user_id != str(OWNER_CHAT_ID): return
        users = load_json(USERS_FILE)
        exported = "\n".join(users.keys())
        chunks = [exported[i:i+4000] for i in range(0, len(exported), 4000)]
        for part in chunks:
            await query.message.reply_text(part)

    elif data == "toggle_bot":
        if user_id != str(OWNER_CHAT_ID): return
        settings = load_json(SETTINGS_FILE)
        is_enabled = settings.get("enabled", True)
        settings["enabled"] = not is_enabled
        save_json(SETTINGS_FILE, settings)
        status = "\u2705 مفعل" if not is_enabled else "\u26d4\ufe0f معطل"
        await query.edit_message_text(f"\u21ba تم تغيير حالة البوت: {status}", reply_markup=back_menu("main"))

    elif data == "edit_welcome":
        if user_id != str(OWNER_CHAT_ID): return
        context.user_data['edit_welcome'] = True
        await query.edit_message_text("\u270d\ufe0f أرسل رسالة الترحيب الجديدة الآن:", reply_markup=back_menu("main"))

    elif data == "view_tickets":
        if user_id != str(OWNER_CHAT_ID): return
        tickets = load_json(TICKETS_FILE)
        if not tickets:
            await query.edit_message_text("\ud83d\udcff لا توجد تذاكر حتى الآن.", reply_markup=back_menu("main"))
            return
        messages = []
        for uid, msgs in tickets.items():
            for msg in msgs:
                messages.append(f"\ud83d\udc64 ID: {uid}\n\ud83d\udce9 {msg}")
        chunks = ["\n\n".join(messages[i:i+5]) for i in range(0, len(messages), 5)]
        for part in chunks:
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=part)
        await query.edit_message_text("\u2705 تم إرسال التذاكر إلى المالك.", reply_markup=back_menu("main"))

    elif data == "block_user":
        if user_id != str(OWNER_CHAT_ID): return
        context.user_data['block_user'] = True
        await query.edit_message_text("\u274c أرسل الآن ID المستخدم الذي تريد حظره:", reply_markup=back_menu("main"))

    elif data == "broadcast":
        if user_id != str(OWNER_CHAT_ID): return
        context.user_data['broadcast'] = True
        await query.edit_message_text("\ud83d\udce2 أرسل الآن الرسالة التي تريد إرسالها لكل المستخدمين:", reply_markup=back_menu("main"))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_chat.id)
    text = update.message.text

    settings = load_json(SETTINGS_FILE)
    if not settings.get("enabled", True) and user_id != str(OWNER_CHAT_ID):
        return

    if context.user_data.get("ticket_mode"):
        context.user_data['ticket_mode'] = False
        tickets = load_json(TICKETS_FILE)
        if user_id not in tickets:
            tickets[user_id] = []
        tickets[user_id].append(text)
        save_json(TICKETS_FILE, tickets)
        await update.message.reply_text("\u2705 تم إرسال تذكرتك بنجاح.")
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=f"\ud83c\udf9f\ufe0f تذكرة جديدة من {update.effective_user.full_name} ({user_id}):\n{text}")
        return

    if context.user_data.get("edit_welcome"):
        context.user_data['edit_welcome'] = False
        with open(WELCOME_FILE, "w", encoding="utf-8") as f:
            f.write(text)
        await update.message.reply_text("\u2705 تم تعديل رسالة الترحيب.")
        return

    if context.user_data.get("block_user"):
        context.user_data['block_user'] = False
        if not text.isdigit():
            await update.message.reply_text("\u274c يجب إرسال ID رقمي صحيح.")
            return
        blocked = load_json(BLOCKED_FILE)
        blocked[text] = True
        save_json(BLOCKED_FILE, blocked)
        await update.message.reply_text(f"\u274c تم حظر المستخدم {text}.")
        return

    if context.user_data.get("broadcast"):
        context.user_data['broadcast'] = False
        users = load_json(USERS_FILE)
        count = 0
        for uid in users:
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                count += 1
            except Exception as e:
                print(f"\u274c Failed to send to {uid}: {e}")
        await update.message.reply_text(f"\ud83d\udce2 تم إرسال الرسالة إلى {count} مستخدم.")
        return

    if context.user_data.get("delete_mode"):
        context.user_data['delete_mode'] = False
        if 'sessionid' not in text:
            await update.message.reply_text("\u274c يرجى إرسال sessionid صالح.")
            return

        await update.message.reply_text("\ud83d\udd04 جاري تنفيذ العملية...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://puppeteer-repost-cleaner.onrender.com/clean", json={"sessionid": text}) as resp:
                    result = await resp.json()
                    if result.get("success"):
                        await update.message.reply_text(f"\u2705 تم حذف {result['deleted']} من الريبوستات بنجاح.")
                    else:
                        await update.message.reply_text(f"\u274c فشل الحذف: {result.get('message', 'غير معروف')}")
        except Exception as e:
            await update.message.reply_text("\u26a0\ufe0f حدث خطأ أثناء التواصل مع الخادم.")
            print("Error:", e)
        return

# ---------- Dashboard Command ----------
async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != OWNER_CHAT_ID:
        await update.message.reply_text("\ud83d\udeab ليس لديك صلاحية الوصول.")
        return
    await update.message.reply_text("\ud83d\udcca لوحة تحكم المالك:", reply_markup=dashboard_menu())

# ---------- Bot Startup ----------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dashboard", dashboard))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print("\u2705 Bot is running...")
    app.run_polling()
