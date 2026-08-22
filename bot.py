import sqlite3
import os
from zoneinfo import ZoneInfo
from datetime import date, timedelta, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

TOKEN = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID = -1004374848256

# -----------------------------
# اعضای گروه
# -----------------------------

MEMBERS = [
    "زهرا",
    "آوا",
    "غزل",
    "امیر محمد",
    "سارا(مؤمن زاده)",
    "آدرین",
    "نفس",
    "آرسین",
    "محیا",
    "رامسس",
    "بنیتا",
    "سارا(خندستانی)",
    "ترانه",
    "بنیامین",
    "طاها"
]

STATUSES = {
    "☄️": "بیشتر از ۶ ساعت",
    "🧨": "بیشتر از ۵ ساعت",
    "💣": "بیشتر از ۴ ساعت",
    "🔥": "بیشتر از ۳ ساعت",
    "💪🏻": "بیشتر از ۲ ساعت",
    "🤩": "بیشتر از ۱ ساعت",
    "✅": "کمتر از ۱ ساعت",
    "🤧": "مریض بودم",
    "✈️": "مسافرت بودم",
    "❌": "تمرین نکردم",
    "😴": "استراحت کردم"
}

# -----------------------------
# ساخت Database
# -----------------------------

def init_database():

    connection = sqlite3.connect("workout.db")

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            telegram_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            workout_day TEXT NOT NULL,
            status TEXT NOT NULL,
            UNIQUE(telegram_id, workout_day)
        )
    """)

    connection.commit()
    connection.close()
# -----------------------------
# /start
# -----------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "سلام! 🤖\n"
        "بات فعال است."
    )

# -----------------------------
# /chatid
# -----------------------------

async def chat_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Chat ID:\n{update.effective_chat.id}"
    )

# -----------------------------
# /register
# -----------------------------



async def register(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    telegram_id = update.effective_user.id

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    # آیا این حساب قبلاً ثبت شده؟
    cursor.execute("""
        SELECT name
        FROM members
        WHERE telegram_id = ?
    """, (telegram_id,))

    existing_member = cursor.fetchone()

    connection.close()

    if existing_member:

        await update.message.reply_text(
            f"شما قبلاً ثبت شده‌اید ✅\n\n"
            f"نام ثبت‌شده: {existing_member[0]}\n\n"
            f"اگر اسم اشتباه است، به مدیر گروه اطلاع بده."
        )

        return

    keyboard = []

    for i in range(0, len(MEMBERS), 2):

        row = []

        row.append(
            InlineKeyboardButton(
                MEMBERS[i],
                callback_data=f"register:{MEMBERS[i]}"
            )
        )

        if i + 1 < len(MEMBERS):

            row.append(
                InlineKeyboardButton(
                    MEMBERS[i + 1],
                    callback_data=f"register:{MEMBERS[i + 1]}"
                )
            )

        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "اسم خودت را انتخاب کن:",
        reply_markup=reply_markup
    )
# -----------------------------
# انتخاب اسم
# -----------------------------

async def register_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    name = query.data.split(":", 1)[1]

    telegram_id = query.from_user.id

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    # بررسی اینکه این حساب قبلاً ثبت نشده باشد
    cursor.execute("""
        SELECT name
        FROM members
        WHERE telegram_id = ?
    """, (telegram_id,))

    existing_member = cursor.fetchone()

    if existing_member:

        connection.close()

        await query.edit_message_text(
            f"شما قبلاً ثبت شده‌اید ✅\n\n"
            f"نام ثبت‌شده: {existing_member[0]}"
        )

        return

    # بررسی اینکه این اسم قبلاً توسط شخص دیگری ثبت نشده باشد
    cursor.execute("""
        SELECT telegram_id
        FROM members
        WHERE name = ?
    """, (name,))

    existing_name = cursor.fetchone()

    if existing_name:

        connection.close()

        await query.edit_message_text(
            "❌ این اسم قبلاً توسط یک حساب دیگر ثبت شده است."
        )

        return

    # ثبت عضو
    cursor.execute("""
        INSERT INTO members (
            telegram_id,
            name
        )
        VALUES (?, ?)
    """, (
        telegram_id,
        name
    ))

    connection.commit()
    connection.close()

    await query.edit_message_text(
        f"ثبت شد ✅\n\n"
        f"نام: {name}"
    )

# -----------------------------
# دریافت پیام‌های گروه
# -----------------------------

DAYS = [
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه"
]


async def group_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    message = update.message.text.strip()

    found_status = None

    # پیدا کردن ایموجی وضعیت
    for emoji in STATUSES:

        if emoji in message:

            # اگر بیش از یک ایموجی وضعیت وجود داشت
            if found_status is not None:

                await update.message.reply_text(
                    "❌ فقط یک ایموجی تمرین در هر پیام مجاز است."
                )

                return

            found_status = emoji

    # اگر هیچ وضعیت معتبری پیدا نشد
    if found_status is None:
        return

    # حذف ایموجی از متن
    workout_day = message.replace(
        found_status,
        ""
    ).strip()

    # بررسی روز تمرین
    if workout_day not in DAYS:

        await update.message.reply_text(
            "❌ روز تمرین معتبر نیست.\n\n"
            "مثال:\n"
            "دوشنبه 🔥"
        )

        return

    telegram_id = update.effective_user.id

    today = date.today().isoformat()

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO workouts (
            telegram_id,
            date,
            workout_day,
            status
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(telegram_id, workout_day)
        DO UPDATE SET
            date = excluded.date,
            status = excluded.status
    """, (
        telegram_id,
        today,
        workout_day,
        found_status
    ))

    connection.commit()
    connection.close()

    await update.message.reply_text(
        f"ثبت شد {found_status}\n"
        f"روز تمرین: {workout_day}\n"
        f"وضعیت: {STATUSES[found_status]}"
    )

async def today_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    today = date.today().isoformat()

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    # گرفتن تمام اعضا
    cursor.execute("""
        SELECT telegram_id, name
        FROM members
    """)

    members = cursor.fetchall()

    # گرفتن تمرین‌های امروز
    cursor.execute("""
        SELECT telegram_id, status
        FROM workouts
        WHERE date = ?
    """, (today,))

    workouts = dict(cursor.fetchall())

    connection.close()

    lines = []

    reported_count = 0

    for telegram_id, name in members:

        if telegram_id in workouts:

            status = workouts[telegram_id]

            lines.append(
                f"{name}    {status}"
            )

            reported_count += 1

        else:

            lines.append(
                f"{name}    ❌"
            )

    report = (
        "📋 گزارش تمرین امروز\n\n"
        + "\n".join(lines)
        + "\n\n"
        + "━━━━━━━━━━━━━━━━\n"
        + f"📊 اعلام کرده‌اند: {reported_count}/{len(members)}"
    )

    await update.message.reply_text(report)

def get_previous_week_dates():

    today = date.today()

    # امروز شنبه است؛ هفته قبل از شنبه تا جمعه بوده
    days_since_saturday = (today.weekday() + 2) % 7

    current_saturday = today - timedelta(
        days=days_since_saturday
    )

    previous_saturday = current_saturday - timedelta(
        days=7
    )

    week_dates = []

    for i in range(7):

        current_day = previous_saturday + timedelta(
            days=i
        )

        week_dates.append(
            current_day.isoformat()
        )

    return week_dates

async def weekly_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    # همه اعضا
    cursor.execute("""
        SELECT telegram_id, name
        FROM members
        ORDER BY rowid
    """)

    members = cursor.fetchall()

    # همه تمرین‌ها
    today = date.today()

    days_since_saturday = (today.weekday() + 2) % 7

    current_saturday = today - timedelta(
        days=days_since_saturday
    )

    week_dates = [
        (
            current_saturday + timedelta(days=i)
        ).isoformat()
        for i in range(7)
    ]

    placeholders = ",".join(
        ["?"] * len(week_dates)
    )

    cursor.execute(
        f"""
        SELECT telegram_id, workout_day, status
        FROM workouts
        WHERE date IN ({placeholders})
        """,
        week_dates
    )
    workouts = cursor.fetchall()

    connection.close()

    # ساخت ساختار:
    # telegram_id -> day -> status
    workout_data = {}

    for telegram_id, workout_day, status in workouts:

        if telegram_id not in workout_data:
            workout_data[telegram_id] = {}

        workout_data[telegram_id][workout_day] = status

    lines = []

    total_reported = 0
    total_possible = len(members) * 7

    for telegram_id, name in members:

        lines.append("")
        lines.append(f"👤 {name}")

        person_reported = 0

        person_data = workout_data.get(
            telegram_id,
            {}
        )

        for day in DAYS:

            if day in person_data:

                status = person_data[day]

                lines.append(
                    f"{day:<10} {status}"
                )

                person_reported += 1
                total_reported += 1

            else:

                lines.append(
                    f"{day:<10} —"
                )

        lines.append(
            f"📊 اعلام‌شده: {person_reported}/7"
        )

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(
        f"📊 مجموع اعلام‌ها: "
        f"{total_reported}/{total_possible}"
    )

    report = (
        "📋 گزارش هفتگی تمرین\n"
        + "\n".join(lines)
    )

    await update.message.reply_text(report)

async def send_weekly_report(context: ContextTypes.DEFAULT_TYPE):

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT telegram_id, name
        FROM members
        ORDER BY rowid
    """)

    members = cursor.fetchall()

    week_dates = get_previous_week_dates()

    placeholders = ",".join(["?"] * len(week_dates))

    cursor.execute(
        f"""
        SELECT telegram_id, workout_day, status
        FROM workouts
        WHERE date IN ({placeholders})
        """,
        week_dates
    )

    workouts = cursor.fetchall()

    connection.close()

    workout_data = {}

    for telegram_id, workout_day, status in workouts:

        if telegram_id not in workout_data:
            workout_data[telegram_id] = {}

        workout_data[telegram_id][workout_day] = status

    lines = ["📋 گزارش هفتگی تمرین\n"]

    total_reported = 0
    total_possible = len(members) * 7

    for telegram_id, name in members:

        lines.append(f"👤 {name}")

        person_data = workout_data.get(
            telegram_id,
            {}
        )

        person_reported = 0

        for day in DAYS:

            if day in person_data:
                status = person_data[day]
                lines.append(f"{day:<10} {status}")

                person_reported += 1
                total_reported += 1

            else:
                lines.append(f"{day:<10} —")

        lines.append(
            f"📊 اعلام‌شده: {person_reported}/7\n"
        )

    lines.append("━━━━━━━━━━━━━━━━")
    lines.append(
        f"📊 مجموع اعلام‌ها: "
        f"{total_reported}/{total_possible}"
    )
        # آمار وضعیت‌ها
    status_counts = {
        emoji: 0
        for emoji in STATUSES
    }

    for telegram_id, workout_day, status in workouts:

        if status in status_counts:
            status_counts[status] += 1

    lines.append("")
    lines.append("📊 آمار کل هفته")
    lines.append("")

    for emoji, count in status_counts.items():

        if count > 0:

            lines.append(
                f"{emoji} {STATUSES[emoji]}: {count}"
            )

    report = "\n".join(lines)

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=report
    )

async def admin_weekly_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not await is_admin(update):

        await update.message.reply_text(
            "❌ این دستور فقط برای ادمین‌های گروه است."
        )

        return
    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT telegram_id, name
        FROM members
        ORDER BY rowid
    """)

    members = cursor.fetchall()

    # برای تست: هفته جاری
    today = date.today()

    days_since_saturday = (today.weekday() + 2) % 7

    current_saturday = today - timedelta(
        days=days_since_saturday
    )

    week_dates = [
        (
            current_saturday + timedelta(days=i)
        ).isoformat()
        for i in range(7)
    ]

    placeholders = ",".join(["?"] * 7)

    cursor.execute(
        f"""
        SELECT telegram_id, workout_day, status
        FROM workouts
        WHERE date IN ({placeholders})
        """,
        week_dates
    )

    workouts = cursor.fetchall()

    connection.close()

    workout_data = {}

    for telegram_id, workout_day, status in workouts:

        if telegram_id not in workout_data:
            workout_data[telegram_id] = {}

        workout_data[telegram_id][workout_day] = status

    lines = ["📋 گزارش تستی هفته جاری\n"]

    for telegram_id, name in members:

        lines.append(f"👤 {name}")

        person_data = workout_data.get(
            telegram_id,
            {}
        )

        for day in DAYS:

            if day in person_data:
                lines.append(
                    f"{day:<10} {person_data[day]}"
                )
            else:
                lines.append(
                    f"{day:<10} —"
                )

        lines.append("")

    report = "\n".join(lines)

    await update.message.reply_text(report)

async def is_admin(
    update: Update
):

    member = await update.effective_chat.get_member(
        update.effective_user.id
    )

    return member.status in [
        "administrator",
        "creator"
    ]

async def last_week_report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # فقط ادمین‌ها
    if not await is_admin(update):
        await update.message.reply_text(
            "❌ این دستور فقط برای ادمین‌های گروه است."
        )
        return

    connection = sqlite3.connect("workout.db")
    cursor = connection.cursor()

    # همه اعضا
    cursor.execute("""
        SELECT telegram_id, name
        FROM members
        ORDER BY rowid
    """)

    members = cursor.fetchall()

    # تاریخ‌های هفته قبل
    week_dates = get_previous_week_dates()

    placeholders = ",".join(
        ["?"] * len(week_dates)
    )

    # تمرین‌های هفته قبل
    cursor.execute(
        f"""
        SELECT telegram_id, workout_day, status
        FROM workouts
        WHERE date IN ({placeholders})
        """,
        week_dates
    )

    workouts = cursor.fetchall()

    connection.close()

    # ساخت:
    # telegram_id -> day -> status
    workout_data = {}

    for telegram_id, workout_day, status in workouts:

        if telegram_id not in workout_data:
            workout_data[telegram_id] = {}

        workout_data[telegram_id][workout_day] = status

    # ساخت گزارش
    lines = ["📋 گزارش هفته قبل\n"]

    total_reported = 0
    total_possible = len(members) * 7

    for telegram_id, name in members:

        lines.append(f"👤 {name}")

        person_data = workout_data.get(
            telegram_id,
            {}
        )

        person_reported = 0

        for day in DAYS:

            if day in person_data:

                status = person_data[day]

                lines.append(
                    f"{day:<10} {status}"
                )

                person_reported += 1
                total_reported += 1

            else:

                lines.append(
                    f"{day:<10} —"
                )

        lines.append(
            f"📊 اعلام‌شده: {person_reported}/7\n"
        )

    lines.append("━━━━━━━━━━━━━━━━")

    lines.append(
        f"📊 مجموع اعلام‌ها: "
        f"{total_reported}/{total_possible}"
    )

    report = (
        "📋 گزارش هفته قبل\n"
        + "\n".join(lines)
    )

    await update.message.reply_text(report)

# -----------------------------
# اجرای برنامه
# -----------------------------

init_database()

app = Application.builder().token(TOKEN).build()
job_queue = app.job_queue

job_queue.run_daily(
    send_weekly_report,
    time=time(
        hour=0,
        minute=0,
        tzinfo=ZoneInfo("Asia/Tehran")
    ),
    days=(5,)
)


app.add_handler(CommandHandler("start", start))

app.add_handler(CommandHandler("register", register))

app.add_handler(
    CommandHandler("today", today_report)
)

app.add_handler(
    CommandHandler("weekly", weekly_report)
)

app.add_handler(
    CommandHandler("chatid", chat_id)
)

app.add_handler(
    CommandHandler("adminweekly", admin_weekly_report)
)

app.add_handler(
    CommandHandler("lastweek", last_week_report)
)

app.add_handler(
    CallbackQueryHandler(
        register_callback,
        pattern="^register:"
    )
)



app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        group_message
    )
)


print("Bot is running...")
print("BOT VERSION 2")
app.run_polling()
