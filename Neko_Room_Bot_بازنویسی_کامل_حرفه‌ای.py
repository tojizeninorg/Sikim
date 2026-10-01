# -*- coding: utf-8 -*-
"""
Neko Room BOT — بازسازی کامل

ویژگی‌های اصلی:
- مدیریت انیمه، فیلم، موسیقی و مانگا
- احراز عضویت در کانال و گروه
- پنل ادمین و مالک
- صف تأیید محتوا
- بکاپ و ارسال همگانی
- بازی گروهی Neko Room با پنل شخصی خصوصی
- ۷ منطقه، ۲۸ بخش و ۳۵۰ آیتم اکتشافی
- دقیقاً ۱۲۰ دستور ساخت ثابت
- استخراج با کول‌داون ثابت ۵ دقیقه
- کلنگ سطح ۱ تا ۱۰ بدون تغییر کول‌داون
- کارخانه، کارگاه، آزمایشگاه و تحقیق
- نبرد شخصی و نبرد پایگاه به‌صورت جدا
- نگهبان، سلاح، زره و دفاع پایگاه
- بازار، مأموریت روزانه، پاداش روزانه و اتحاد
- پشتیبان‌گیری و مدیریت عکس آیتم‌ها

توکن به‌صورت مستقیم در متغیر `TOKEN` در ابتدای همین فایل قرار می‌گیرد؛ فقط توکن BotFather را بین کوتیشن‌ها Paste کن.
"""

import asyncio
import json
import os
import random
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

try:
    from telegram import (
        Update,
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        ReplyKeyboardMarkup,
        ReplyKeyboardRemove,
    )
    from telegram.constants import ChatType
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
except ModuleNotFoundError as exc:
    if exc.name == "telegram":
        raise RuntimeError(
            "کتابخانه python-telegram-bot نصب نیست.\n"
            "در Pydroid 3 این دستور را اجرا کن:\n"
            "pip install -U python-telegram-bot"
        ) from exc
    raise

# =========================================================
# پیکربندی و مسیرهای مطمئن
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backup"
GAME_DIR = DATA_DIR / "game"
for _folder in (DATA_DIR, BACKUP_DIR, GAME_DIR):
    _folder.mkdir(parents=True, exist_ok=True)

OWNER_ID = 7221243573
ADMIN_IDS = [
    6796344029,
    7214060194,
    7069611670,
    931818091,
    8737164214,
]
FORCED_CHANNEL = "@nekoroomchannel"
# ربات دیگر به یک گروه خاص وابسته نیست؛ هر گروهی که ربات داخل آن باشد می‌تواند از
# میانبرهای بازی و قابلیت‌های گروهی ربات استفاده کند.
SUPPORT_USERNAME = "@YOUR_SUPPORT_ID"


# =========================================================
# توکن ربات
# فقط توکن BotFather را داخل کوتیشن زیر قرار بده
# مثال:
# TOKEN = "123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# =========================================================
TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

if not TOKEN.strip() or TOKEN.strip() == "PASTE_YOUR_BOT_TOKEN_HERE":
    raise RuntimeError(
        "❌ توکن ربات را در ابتدای فایل، مقابل TOKEN = قرار بده.\n"
        "مثال: TOKEN = \"توکن_بات_از_BotFather\""
    )

TOKEN_SOURCE = "توکن قرارگرفته در کد"

USERS_FILE = DATA_DIR / "users.json"
ADMINS_FILE = DATA_DIR / "admins.json"
CONTENT_FILE = DATA_DIR / "content.json"
REQUESTS_FILE = DATA_DIR / "requests.json"
ACTIVITY_FILE = DATA_DIR / "activity.json"

# =========================================================
# JSON امن
# =========================================================

def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_json(path, default):
    path = Path(path)
    try:
        if not path.exists():
            save_json(path, default)
            return default
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, type(default)):
            return default
        return data
    except Exception:
        # فایل خراب باعث توقف کامل ربات نمی‌شود.
        return default


users = load_json(USERS_FILE, [])
admins = load_json(ADMINS_FILE, [])
contents = load_json(CONTENT_FILE, [])
requests = load_json(REQUESTS_FILE, [])
activity = load_json(ACTIVITY_FILE, [])

if not ADMINS_FILE.exists() or not admins:
    admins = list(dict.fromkeys(ADMIN_IDS))
    save_json(ADMINS_FILE, admins)
else:
    admins = [int(x) for x in admins if str(x).isdigit()]

# =========================================================
# ابزارهای عمومی
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize(text):
    if not text:
        return ""
    return str(text).strip().lower().replace("ي", "ی").replace("ك", "ک")


def is_owner(user_id):
    return user_id == OWNER_ID


def is_admin(user_id):
    return user_id == OWNER_ID or user_id in admins


def get_user(user_id):
    for user in users:
        if user.get("id") == user_id:
            return user
    return None


def register_user(user):
    if not user:
        return
    record = get_user(user.id)
    if record:
        record["username"] = user.username
        record["first_name"] = user.first_name
        record["last_seen"] = now()
        record.setdefault("points", 0)
    else:
        users.append({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_seen": now(),
            "downloads": 0,
            "favorites": [],
            "history": [],
            "following": [],
            "points": 0,
        })
    save_json(USERS_FILE, users)


def log_activity(user_id, action, details=""):
    activity.append({"user_id": user_id, "action": action, "details": details, "time": now()})
    if len(activity) > 5000:
        del activity[:-5000]
    save_json(ACTIVITY_FILE, activity)


def get_content(content_id):
    for item in contents:
        if item.get("id") == content_id:
            return item
    return None


def new_id(prefix):
    return f"{prefix}_{int(datetime.now().timestamp() * 1000)}"


def get_request(request_id):
    for request in requests:
        if request.get("id") == request_id:
            return request
    return None


def category_name(category):
    return {
        "anime": "🎬 انیمه",
        "movie": "🎥 فیلم",
        "music": "🎵 موسیقی",
        "manga": "📚 مانگا",
    }.get(category, str(category or "نامشخص"))


async def delete_later(bot, chat_id, message_id, seconds=30):
    await asyncio.sleep(seconds)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


def schedule_delete(message, seconds=30):
    try:
        asyncio.create_task(delete_later(message.get_bot(), message.chat_id, message.message_id, seconds))
    except Exception:
        pass


# MAIN KEYBOARD
# =========================================================

def main_keyboard(user_id):

    rows = [
        ["🎬 انیمه", "🎥 فیلم"],
        ["🎵 موسیقی", "📚 مانگا"],
        ["🔎 جستجو", "🆕 تازه‌ها"],
        ["🔥 محبوب‌ها", "🎲 پیشنهاد تصادفی"],
        ["⭐ علاقه‌مندی‌ها", "🕘 تاریخچه"],
    ]

    if is_admin(user_id):
        rows.append(
            ["⚙️ پنل مدیریت"]
        )

    if is_owner(user_id):
        rows.append(
            ["👑 پنل مالک"]
        )

    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True
    )


# =========================================================
# MEMBERSHIP
# =========================================================

async def check_membership(bot, user_id):

    if is_admin(user_id):
        return True

    try:

        channel_member = await bot.get_chat_member(
            FORCED_CHANNEL,
            user_id
        )

        valid = [
            "member",
            "administrator",
            "creator"
        ]

        # عضویت در یک گروه خاص دیگر اجباری نیست؛ ربات باید در هر گروهی
        # که به آن اضافه شده قابل استفاده باشد.
        return channel_member.status in valid

    except Exception:
        return False


async def membership_message(update):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 عضویت در کانال",
                url="https://t.me/nekoroomchannel"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data="check_membership"
            )
        ]
    ])

    target = update.effective_message
    if target:
        await target.reply_text(
            "🔒 برای استفاده از بخش‌های محتوایی ابتدا در کانال Neko Room عضو شو.\n"
            "🎮 قابلیت‌های بازی و گروهی در هر گروهی که ربات داخل آن باشد در دسترس هستند.",
            reply_markup=keyboard
        )

# =========================================================
# START
# =========================================================

async def start(update, context):

    user = update.effective_user

    register_user(user)

    # لینک مستقیم بازی: /start game
    if getattr(context, "args", None) and "game" in context.args:
        p = game_player(user)
        context.user_data.clear()
        await update.message.reply_text(
            game_profile_text(p),
            reply_markup=game_main_keyboard(user.id)
        )
        return

    if not await check_membership(
        context.bot,
        user.id
    ):
        await membership_message(update)
        return

    context.user_data.clear()

    await update.message.reply_text(
        "🏠 به Neko Room خوش اومدی.\n\n"
        "از منوی پایین یکی از بخش‌ها رو انتخاب کن.",
        reply_markup=main_keyboard(
            user.id
        )
    )


# =========================================================
# CATEGORY
# =========================================================

async def show_category(update, category):

    items = [
        x for x in contents
        if x.get("category") == category
    ]

    if not items:
        await update.message.reply_text(
            "فعلاً چیزی در این بخش اضافه نشده."
        )
        return

    keyboard = []

    for item in items:
        keyboard.append([
            InlineKeyboardButton(
                item.get(
                    "name",
                    "بدون نام"
                ),
                callback_data=(
                    f"content:{item['id']}"
                )
            )
        ])

    await update.message.reply_text(
        category_name(category),
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# CONTENT
# =========================================================

async def content_callback(update, context):

    query = update.callback_query
    await query.answer()

    if not await check_membership(
        context.bot,
        query.from_user.id
    ):
        await query.answer(
            "❌ ابتدا عضو کانال Neko Room شو.",
            show_alert=True
        )
        return

    content_id = query.data.split(
        ":",
        1
    )[1]

    content = get_content(
        content_id
    )

    if not content:
        await query.message.reply_text(
            "❌ محتوا پیدا نشد."
        )
        return

    keyboard = []

    if content.get("category") == "anime":

        for season in content.get(
            "seasons",
            []
        ):

            keyboard.append([
                InlineKeyboardButton(
                    f"📀 فصل {season.get('season')}",
                    callback_data=(
                        f"season:"
                        f"{content_id}:"
                        f"{season.get('season')}"
                    )
                )
            ])

    else:

        for index, file in enumerate(
            content.get("files", []),
            1
        ):

            keyboard.append([
                InlineKeyboardButton(
                    f"▶️ فایل {index}",
                    callback_data=(
                        f"file:"
                        f"{content_id}:"
                        f"{index - 1}"
                    )
                )
            ])

    user = get_user(
        query.from_user.id
    )

    favorites = (
        user.get("favorites", [])
        if user
        else []
    )

    if content_id in favorites:
        fav_text = "💔 حذف از علاقه‌مندی‌ها"
    else:
        fav_text = "⭐ افزودن به علاقه‌مندی‌ها"

    keyboard.append([
        InlineKeyboardButton(
            fav_text,
            callback_data=f"fav:{content_id}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ برگشت",
            callback_data="back_main"
        )
    ])

    await query.message.reply_text(
        f"📌 {content.get('name')}\n\n"
        f"📂 {category_name(content.get('category'))}\n"
        f"⬇️ دانلودها: "
        f"{content.get('downloads', 0)}",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# SEASON
# =========================================================

async def season_callback(update, context):

    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    content_id = parts[1]
    season_number = int(parts[2])

    content = get_content(
        content_id
    )

    if not content:
        return

    season = None

    for item in content.get(
        "seasons",
        []
    ):

        if int(
            item.get("season", 0)
        ) == season_number:

            season = item
            break

    if not season:
        return

    keyboard = []

    for episode in season.get(
        "episodes",
        []
    ):

        keyboard.append([
            InlineKeyboardButton(
                f"▶️ قسمت {episode.get('episode')}",
                callback_data=(
                    f"episode:"
                    f"{content_id}:"
                    f"{season_number}:"
                    f"{episode.get('episode')}"
                )
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ برگشت",
            callback_data=(
                f"content:{content_id}"
            )
        )
    ])

    await query.message.reply_text(
        f"🎬 {content.get('name')}\n"
        f"📀 فصل {season_number}",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# SEND CONTENT FILE
# =========================================================

async def send_saved_file(
    bot,
    chat_id,
    file
):

    file_id = file.get("file_id")
    file_type = file.get("type", "document")
    sent = None
    if file_type == "video":
        sent = await bot.send_video(chat_id, file_id)
    elif file_type == "audio":
        sent = await bot.send_audio(chat_id, file_id)
    elif file_type == "photo":
        sent = await bot.send_photo(chat_id, file_id)
    else:
        sent = await bot.send_document(chat_id, file_id)
    try:
        asyncio.create_task(delete_later(bot, sent.chat_id, sent.message_id, 30))
    except Exception:
        pass
    return sent


def increment_download(
    user_id,
    content_id
):

    user = get_user(user_id)

    if user:

        user["downloads"] = (
            user.get("downloads", 0)
            + 1
        )

        history = user.setdefault(
            "history",
            []
        )

        if content_id in history:
            history.remove(content_id)

        history.insert(
            0,
            content_id
        )

        del history[30:]

    content = get_content(
        content_id
    )

    if content:
        content["downloads"] = (
            content.get("downloads", 0)
            + 1
        )

    save_json(
        USERS_FILE,
        users
    )

    save_json(
        CONTENT_FILE,
        contents
    )


# =========================================================
# EPISODE
# =========================================================

async def episode_callback(update, context):

    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    content_id = parts[1]
    season_number = int(parts[2])
    episode_number = int(parts[3])
    destination_chat_id = (
        query.message.chat.id
        if query.message and query.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
        else query.from_user.id
    )

    content = get_content(
        content_id
    )

    if not content:
        return

    for season in content.get(
        "seasons",
        []
    ):

        if int(
            season.get("season", 0)
        ) != season_number:
            continue

        for episode in season.get(
            "episodes",
            []
        ):

            if int(
                episode.get("episode", 0)
            ) != episode_number:
                continue

            try:

                await send_saved_file(
                    context.bot,
                    destination_chat_id,
                    episode
                )

                increment_download(
                    query.from_user.id,
                    content_id
                )

                log_activity(
                    query.from_user.id,
                    "download",
                    f"{content.get('name')} "
                    f"S{season_number}E{episode_number}"
                )

            except Exception:
                await query.message.reply_text(
                    "❌ ارسال فایل ناموفق بود."
                )

            return


# =========================================================
# NORMAL FILE
# =========================================================

async def file_callback(update, context):

    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    content_id = parts[1]
    index = int(parts[2])
    destination_chat_id = (
        query.message.chat.id
        if query.message and query.message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
        else query.from_user.id
    )

    content = get_content(
        content_id
    )

    if not content:
        return

    files = content.get(
        "files",
        []
    )

    if index >= len(files):
        return

    try:

        await send_saved_file(
            context.bot,
            destination_chat_id,
            files[index]
        )

        increment_download(
            query.from_user.id,
            content_id
        )

        log_activity(
            query.from_user.id,
            "download",
            content.get("name")
        )

    except Exception:
        await query.message.reply_text(
            "❌ ارسال فایل ناموفق بود."
        )


# =========================================================
# FAVORITES
# =========================================================

async def favorite_callback(update, context):

    query = update.callback_query

    content_id = query.data.split(
        ":",
        1
    )[1]

    user = get_user(
        query.from_user.id
    )

    if not user:
        await query.answer()
        return

    favorites = user.setdefault(
        "favorites",
        []
    )

    if content_id in favorites:

        favorites.remove(
            content_id
        )

        text = "💔 از علاقه‌مندی‌ها حذف شد."

    else:

        favorites.append(
            content_id
        )

        text = "⭐ به علاقه‌مندی‌ها اضافه شد."

    save_json(
        USERS_FILE,
        users
    )

    await query.answer(
        text,
        show_alert=True
    )


async def show_favorites(update):

    user = get_user(
        update.effective_user.id
    )

    if not user:
        return

    keyboard = []

    for content_id in user.get(
        "favorites",
        []
    ):

        content = get_content(
            content_id
        )

        if content:
            keyboard.append([
                InlineKeyboardButton(
                    content.get("name"),
                    callback_data=(
                        f"content:{content_id}"
                    )
                )
            ])

    if not keyboard:
        await update.message.reply_text(
            "⭐ هنوز چیزی به علاقه‌مندی‌ها اضافه نکردی."
        )
        return

    await update.message.reply_text(
        "⭐ علاقه‌مندی‌ها",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# HISTORY
# =========================================================

async def show_history(update):

    user = get_user(
        update.effective_user.id
    )

    if not user:
        return

    keyboard = []

    for content_id in user.get(
        "history",
        []
    ):

        content = get_content(
            content_id
        )

        if content:

            keyboard.append([
                InlineKeyboardButton(
                    content.get("name"),
                    callback_data=(
                        f"content:{content_id}"
                    )
                )
            ])

    if not keyboard:
        await update.message.reply_text(
            "🕘 هنوز سابقه‌ای وجود ندارد."
        )
        return

    await update.message.reply_text(
        "🕘 تاریخچه",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# NEW
# =========================================================

async def show_new(update):

    items = sorted(
        contents,
        key=lambda x: x.get(
            "created_at",
            ""
        ),
        reverse=True
    )[:20]

    if not items:
        await update.message.reply_text(
            "هنوز محتوایی اضافه نشده."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                item.get("name"),
                callback_data=(
                    f"content:{item['id']}"
                )
            )
        ]
        for item in items
    ]

    await update.message.reply_text(
        "🆕 تازه‌ها",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# POPULAR
# =========================================================

async def show_popular(update):

    items = sorted(
        contents,
        key=lambda x: x.get(
            "downloads",
            0
        ),
        reverse=True
    )[:20]

    if not items:
        await update.message.reply_text(
            "هنوز محتوایی وجود ندارد."
        )
        return

    keyboard = []

    for item in items:

        keyboard.append([
            InlineKeyboardButton(
                f"🔥 {item.get('name')} "
                f"({item.get('downloads', 0)})",
                callback_data=(
                    f"content:{item['id']}"
                )
            )
        ])

    await update.message.reply_text(
        "🔥 محبوب‌ها",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# RANDOM
# =========================================================

async def random_content(update):

    if not contents:
        await update.message.reply_text(
            "هنوز محتوایی وجود ندارد."
        )
        return

    item = random.choice(
        contents
    )

    await update.message.reply_text(
        f"🎲 پیشنهاد تصادفی:\n\n"
        f"📌 {item.get('name')}",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "▶️ مشاهده",
                    callback_data=(
                        f"content:{item['id']}"
                    )
                )
            ]
        ])
    )


# =========================================================
# SEARCH
# =========================================================

async def start_search(update, context):

    context.user_data["state"] = "search"

    await update.message.reply_text(
        "🔎 نام محتوا را بنویس:"
    )


async def search_content(update, context):

    query_text = normalize(
        update.message.text
    )

    results = [
        item
        for item in contents
        if query_text in normalize(
            item.get("name")
        )
    ]

    context.user_data.clear()

    if not results:
        await update.message.reply_text(
            "❌ چیزی پیدا نشد."
        )
        return

    keyboard = [
        [
            InlineKeyboardButton(
                item.get("name"),
                callback_data=(
                    f"content:{item['id']}"
                )
            )
        ]
        for item in results[:30]
    ]

    await update.message.reply_text(
        f"🔎 {len(results)} نتیجه:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ افزودن انیمه",
                callback_data="add:anime"
            )
        ],

        [
            InlineKeyboardButton(
                "➕ افزودن فیلم",
                callback_data="add:movie"
            ),
            InlineKeyboardButton(
                "➕ افزودن موسیقی",
                callback_data="add:music"
            )
        ],

        [
            InlineKeyboardButton(
                "➕ افزودن مانگا",
                callback_data="add:manga"
            )
        ],

        [
            InlineKeyboardButton(
                "📂 محتواهای من",
                callback_data="my_contents"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار من",
                callback_data="my_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "📩 ارتباط با مالک",
                callback_data="contact_owner"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ برگشت",
                callback_data="back_main"
            )
        ]
    ])


async def admin_panel(update):

    if not is_admin(
        update.effective_user.id
    ):
        return

    await update.message.reply_text(
        "⚙️ پنل مدیریت",
        reply_markup=admin_keyboard()
    )


# =========================================================
# ADD CONTENT
# =========================================================

async def add_callback(update, context):

    query = update.callback_query
    await query.answer()

    if not is_admin(
        query.from_user.id
    ):
        return

    category = query.data.split(
        ":"
    )[1]

    context.user_data.clear()

    context.user_data["adding"] = True
    context.user_data["category"] = category
    context.user_data["state"] = "add_name"
    context.user_data["upload_files"] = []

    await query.message.reply_text(
        "📝 اسم محتوا را بفرست:"
    )


async def receive_name(update, context):

    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "❌ نام معتبر نیست."
        )
        return

    category = context.user_data.get(
        "category"
    )

    context.user_data["name"] = name

    if category == "anime":

        context.user_data["state"] = (
            "add_season"
        )

        await update.message.reply_text(
            "📀 شماره فصل را وارد کن:\n\n"
            "مثلاً: 1"
        )

    else:

        context.user_data["state"] = (
            "add_files"
        )

        await update.message.reply_text(
            "📤 فایل‌ها را یکی‌یکی بفرست.\n\n"
            "بعد از تمام شدن، دکمه «✅ پایان» را بزن.",
            reply_markup=ReplyKeyboardMarkup(
                [["✅ پایان"]],
                resize_keyboard=True
            )
        )


# =========================================================
# SEASON
# =========================================================

async def receive_season(update, context):

    try:

        season = int(
            update.message.text.strip()
        )

        if season < 1:
            raise ValueError

    except ValueError:

        await update.message.reply_text(
            "❌ شماره فصل باید یک عدد مثبت باشد."
        )
        return

    context.user_data["season"] = season
    context.user_data["state"] = "add_files"
    context.user_data["upload_files"] = []

    await update.message.reply_text(
        f"📀 فصل {season} انتخاب شد.\n\n"
        "فایل قسمت‌ها را دقیقاً به ترتیبی "
        "که می‌خواهی ارسال کن.\n\n"
        "فایل اول = قسمت ۱\n"
        "فایل دوم = قسمت ۲\n"
        "فایل سوم = قسمت ۳\n\n"
        "بعد از اتمام «✅ پایان» را بزن.",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ پایان"]],
            resize_keyboard=True
        )
    )


# =========================================================
# FILE EXTRACT
# =========================================================

def extract_file(message):

    if message.video:

        return {
            "file_id": message.video.file_id,
            "type": "video"
        }

    if message.document:

        return {
            "file_id": message.document.file_id,
            "type": "document"
        }

    if message.audio:

        return {
            "file_id": message.audio.file_id,
            "type": "audio"
        }

    if message.photo:

        return {
            "file_id": message.photo[-1].file_id,
            "type": "photo"
        }

    return None


async def receive_file(update, context):

    if not is_admin(
        update.effective_user.id
    ):
        return

    file = extract_file(
        update.message
    )

    if not file:
        return

    files = context.user_data.setdefault(
        "upload_files",
        []
    )

    files.append(file)

    await update.message.reply_text(
        f"✅ فایل شماره {len(files)} دریافت شد."
    )


# =========================================================
# FINISH UPLOAD
# =========================================================

async def finish_upload(update, context):

    user_id = update.effective_user.id

    if not is_admin(user_id):
        return

    category = context.user_data.get(
        "category"
    )

    name = context.user_data.get(
        "name"
    )

    files = context.user_data.get(
        "upload_files",
        []
    )

    if not category or not name:

        context.user_data.clear()

        await update.message.reply_text(
            "❌ اطلاعات درخواست ناقص است.",
            reply_markup=ReplyKeyboardRemove()
        )

        return

    if not files:

        await update.message.reply_text(
            "❌ حداقل یک فایل ارسال کن."
        )

        return

    # ساخت درخواست
    request = {
        "id": new_id("request"),
        "admin_id": user_id,
        "admin_name": update.effective_user.first_name,
        "admin_username": update.effective_user.username,
        "category": category,
        "name": name,
        "season": context.user_data.get(
            "season"
        ),
        "files": files,
        "created_at": now(),
        "status": "pending"
    }

    requests.append(request)

    save_json(
        REQUESTS_FILE,
        requests
    )

    # پیام به مالک
    text = (
        "📨 درخواست جدید برای تأیید\n\n"
        f"👤 ادمین: "
        f"{request['admin_name']}\n"
        f"🆔 آیدی: "
        f"{user_id}\n"
        f"📂 نوع: "
        f"{category_name(category)}\n"
        f"📌 نام: "
        f"{name}\n"
    )

    if category == "anime":

        text += (
            f"📀 فصل: "
            f"{request['season']}\n"
            f"▶️ تعداد قسمت: "
            f"{len(files)}\n"
        )

    else:

        text += (
            f"📁 تعداد فایل: "
            f"{len(files)}\n"
        )

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "✅ تأیید",
                callback_data=(
                    f"approve:{request['id']}"
                )
            ),

            InlineKeyboardButton(
                "❌ رد",
                callback_data=(
                    f"reject:{request['id']}"
                )
            )
        ]
    ])

    try:

        await context.bot.send_message(
            OWNER_ID,
            text,
            reply_markup=keyboard
        )

    except Exception as e:

        print(
            "OWNER REQUEST ERROR:",
            e
        )

        await update.message.reply_text(
            "❌ ارسال درخواست برای مالک انجام نشد."
        )

        return

    context.user_data.clear()

    await update.message.reply_text(
        "📨 درخواست برای مالک ارسال شد.\n\n"
        "⏳ بعد از تأیید مالک، همین فایل‌ها "
        "خودکار ثبت می‌شوند و نیازی به "
        "ارسال دوباره نیست.",
        reply_markup=ReplyKeyboardRemove()
    )


# =========================================================
# APPROVE REQUEST
# =========================================================

async def approve_request(update, context):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "⛔ فقط مالک دسترسی دارد.",
            show_alert=True
        )

        return

    await query.answer()

    request_id = query.data.split(
        ":",
        1
    )[1]

    request = get_request(
        request_id
    )

    if not request:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request.get("status") != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    category = request["category"]
    name = request["name"]
    files = request["files"]
    admin_id = request["admin_id"]

    # =====================================================
    # ANIME
    # =====================================================

    if category == "anime":

        season_number = request.get(
            "season"
        )

        content = None

        for item in contents:

            if (
                item.get("category") == "anime"
                and normalize(
                    item.get("name")
                ) == normalize(name)
            ):

                content = item
                break

        episodes = []

        for index, file in enumerate(
            files,
            1
        ):

            episodes.append({
                "episode": index,
                "file_id": file["file_id"],
                "type": file["type"]
            })

        if content:

            for old_season in content.get(
                "seasons",
                []
            ):

                if int(
                    old_season.get(
                        "season",
                        0
                    )
                ) == int(
                    season_number
                ):

                    await query.message.reply_text(
                        "⚠️ این فصل قبلاً ثبت شده."
                    )

                    request["status"] = "rejected"
                    request["reviewed_at"] = now()
                    request["reviewed_by"] = OWNER_ID

                    save_json(
                        REQUESTS_FILE,
                        requests
                    )

                    return

            content.setdefault(
                "seasons",
                []
            ).append({
                "season": season_number,
                "episodes": episodes
            })

            content["seasons"].sort(
                key=lambda x: int(
                    x.get("season", 0)
                )
            )

            content_id = content["id"]

        else:

            content_id = new_id(
                "content"
            )

            contents.append({

                "id": content_id,

                "name": name,

                "category": "anime",

                "owner_id": admin_id,

                "created_at": now(),

                "downloads": 0,

                "seasons": [
                    {
                        "season": season_number,
                        "episodes": episodes
                    }
                ]
            })

    # =====================================================
    # OTHER CONTENT
    # =====================================================

    else:

        content = None

        for item in contents:

            if (
                item.get("category") == category
                and normalize(
                    item.get("name")
                ) == normalize(name)
            ):

                content = item
                break

        if content:

            content.setdefault(
                "files",
                []
            ).extend(files)

            content_id = content["id"]

        else:

            content_id = new_id(
                "content"
            )

            contents.append({

                "id": content_id,

                "name": name,

                "category": category,

                "owner_id": admin_id,

                "created_at": now(),

                "downloads": 0,

                "files": files
            })

    # ذخیره
    save_json(
        CONTENT_FILE,
        contents
    )

    # تغییر وضعیت درخواست
    request["status"] = "approved"
    request["reviewed_at"] = now()
    request["reviewed_by"] = OWNER_ID
    request["content_id"] = content_id

    save_json(
        REQUESTS_FILE,
        requests
    )

    log_activity(
        OWNER_ID,
        "approve_request",
        f"{name} - {admin_id}"
    )

    # اطلاع به ادمین
    try:

        message = (
            "✅ درخواستت توسط مالک تأیید شد.\n\n"
            f"📌 {name}\n"
        )

        if category == "anime":

            message += (
                f"📀 فصل {season_number}\n"
            )

        message += (
            "\n📂 محتوا به صورت خودکار ثبت شد."
        )

        await context.bot.send_message(
            admin_id,
            message
        )

    except Exception:
        pass

    await query.edit_message_reply_markup(
        reply_markup=None
    )

    await query.message.reply_text(
        f"✅ «{name}» تأیید و ثبت شد."
    )


# =========================================================
# REJECT REQUEST
# =========================================================

async def reject_request(update, context):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):

        await query.answer(
            "⛔ فقط مالک دسترسی دارد.",
            show_alert=True
        )

        return

    await query.answer()

    request_id = query.data.split(
        ":",
        1
    )[1]

    request = get_request(
        request_id
    )

    if not request:

        await query.message.reply_text(
            "❌ درخواست پیدا نشد."
        )

        return

    if request.get("status") != "pending":

        await query.message.reply_text(
            "⚠️ این درخواست قبلاً بررسی شده."
        )

        return

    request["status"] = "rejected"
    request["reviewed_at"] = now()
    request["reviewed_by"] = OWNER_ID

    save_json(
        REQUESTS_FILE,
        requests
    )

    try:

        await context.bot.send_message(
            request["admin_id"],
            "❌ درخواستت توسط مالک رد شد.\n\n"
            f"📌 {request['name']}"
        )

    except Exception:
        pass

    log_activity(
        OWNER_ID,
        "reject_request",
        request["name"]
    )

    await query.edit_message_reply_markup(
        reply_markup=None
    )

    await query.message.reply_text(
        f"❌ درخواست «{request['name']}» رد شد."
    )


# =========================================================
# OWNER REQUESTS
# =========================================================

async def owner_requests(update, context):

    query = update.callback_query

    if not is_owner(
        query.from_user.id
    ):
        return

    await query.answer()

    pending = [
        request
        for request in requests
        if request.get("status") == "pending"
    ]

    if not pending:

        await query.message.reply_text(
            "📨 هیچ درخواست در انتظاری وجود ندارد."
        )

        return

    for request in pending:

        text = (
            "📨 درخواست در انتظار\n\n"
            f"👤 {request.get('admin_name')}\n"
            f"🆔 {request.get('admin_id')}\n"
            f"📂 {category_name(request.get('category'))}\n"
            f"📌 {request.get('name')}\n"
        )

        if request.get(
            "category"
        ) == "anime":

            text += (
                f"📀 فصل: "
                f"{request.get('season')}\n"
            )

        text += (
            f"📁 فایل‌ها: "
            f"{len(request.get('files', []))}"
        )

        keyboard = InlineKeyboardMarkup([

            [
                InlineKeyboardButton(
                    "✅ تأیید",
                    callback_data=(
                        f"approve:{request['id']}"
                    )
                ),

                InlineKeyboardButton(
                    "❌ رد",
                    callback_data=(
                        f"reject:{request['id']}"
                    )
                )
            ]

        ])

        await query.message.reply_text(
            text,
            reply_markup=keyboard
        )


# =========================================================
# ADMIN CONTENTS
# =========================================================

async def my_contents(update, context):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    items = [
        item
        for item in contents
        if item.get("owner_id") == user_id
    ]

    if not items:

        await query.message.reply_text(
            "📂 هنوز محتوایی ثبت نکردی."
        )

        return

    keyboard = []

    for item in items:

        keyboard.append([
            InlineKeyboardButton(
                f"⚙️ {item.get('name')}",
                callback_data=(
                    f"manage:{item['id']}"
                )
            )
        ])

    await query.message.reply_text(
        "📂 محتواهای من",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# MANAGE CONTENT
# =========================================================

async def manage_content(update, context):

    query = update.callback_query
    await query.answer()

    content_id = query.data.split(
        ":",
        1
    )[1]

    content = get_content(
        content_id
    )

    if not content:
        return

    if (
        content.get("owner_id")
        != query.from_user.id
        and
        not is_owner(
            query.from_user.id
        )
    ):
        return

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🗑 حذف محتوا",
                callback_data=(
                    f"delete:{content_id}"
                )
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ برگشت",
                callback_data="back_main"
            )
        ]
    ])

    await query.message.reply_text(
        f"⚙️ مدیریت محتوا\n\n"
        f"📌 {content.get('name')}",
        reply_markup=keyboard
    )


# =========================================================
# DELETE
# =========================================================

async def delete_content(update, context):

    query = update.callback_query
    await query.answer()

    content_id = query.data.split(
        ":",
        1
    )[1]

    content = get_content(
        content_id
    )

    if not content:
        return

    if (
        content.get("owner_id")
        != query.from_user.id
        and
        not is_owner(
            query.from_user.id
        )
    ):
        await query.answer(
            "⛔ دسترسی ندارید.",
            show_alert=True
        )
        return

    contents.remove(
        content
    )

    save_json(
        CONTENT_FILE,
        contents
    )

    log_activity(
        query.from_user.id,
        "delete_content",
        content.get("name")
    )

    await query.message.reply_text(
        f"🗑 «{content.get('name')}» حذف شد."
    )


# =========================================================
# ADMIN STATS
# =========================================================

async def admin_stats(update, context):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    items = [
        item
        for item in contents
        if item.get("owner_id") == user_id
    ]

    downloads = sum(
        item.get("downloads", 0)
        for item in items
    )

    await query.message.reply_text(
        "📊 آمار من\n\n"
        f"📂 محتواها: {len(items)}\n"
        f"⬇️ دانلودها: {downloads}"
    )


# =========================================================
# CONTACT ADMIN → OWNER
# =========================================================

async def contact_owner(update, context):

    query = update.callback_query
    await query.answer()

    if (
        not is_admin(
            query.from_user.id
        )
        or
        is_owner(
            query.from_user.id
        )
    ):
        return

    context.user_data["state"] = (
        "contact_owner"
    )

    await query.message.reply_text(
        "📩 پیام خودت برای مالک را بنویس:"
    )


# =========================================================
# OWNER → ADMIN LIST
# =========================================================

async def owner_contact_admins(
    update,
    context
):

    query = update.callback_query
    await query.answer()

    if not is_owner(
        query.from_user.id
    ):
        return

    admin_ids = [
        admin_id
        for admin_id in admins
        if admin_id != OWNER_ID
    ]

    if not admin_ids:

        await query.message.reply_text(
            "👮 ادمینی وجود ندارد."
        )

        return

    keyboard = []

    for admin_id in admin_ids:

        user = get_user(admin_id)
        name = user.get("first_name", "-") if user else "-"
        username = user.get("username") if user else None

        if not user or not username:
            try:
                chat = await context.bot.get_chat(admin_id)
                name = chat.full_name or name or "-"
                username = chat.username or username
            except Exception:
                pass

        if username:
            label = f"{name} | @{username} | ID: {admin_id}"
        else:
            label = f"{name} | ID: {admin_id}"

        keyboard.append([

            InlineKeyboardButton(
                label,
                callback_data=(
                    f"contact_admin:{admin_id}"
                )
            )

        ])

    await query.message.reply_text(
        "👥 ادمینی که می‌خواهی به او پیام بدهی را انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(
            keyboard
        )
    )


# =========================================================
# SELECT ADMIN
# =========================================================

async def select_admin(update, context):

    query = update.callback_query
    await query.answer()

    if not is_owner(
        query.from_user.id
    ):
        return

    admin_id = int(
        query.data.split(
            ":",
            1
        )[1]
    )

    if admin_id not in admins:

        await query.message.reply_text(
            "❌ این شخص دیگر ادمین نیست."
        )

        return

    context.user_data["state"] = (
        "contact_admin"
    )

    context.user_data["contact_admin"] = (
        admin_id
    )

    await query.message.reply_text(
        "📩 پیام برای این ادمین را بنویس:"
    )


# =========================================================
# CONTACT ROUTER
# =========================================================

async def contact_text(update, context):

    state = context.user_data.get(
        "state"
    )

    user_id = update.effective_user.id
    text = update.message.text.strip()

    # ادمین → مالک
    if state == "contact_owner":

        if (
            not is_admin(user_id)
            or is_owner(user_id)
        ):
            context.user_data.clear()
            return

        user = get_user(user_id)

        name = (
            user.get("first_name")
            if user
            else update.effective_user.first_name
        )

        username = (
            user.get("username")
            if user
            else update.effective_user.username
        )

        message = (
            "📩 پیام از طرف ادمین\n\n"
            f"👤 {name}\n"
            f"🆔 {user_id}\n"
        )

        if username:
            message += (
                f"🔹 @{username}\n"
            )

        message += (
            f"\n💬 {text}"
        )

        try:

            await context.bot.send_message(
                OWNER_ID,
                message
            )

            await update.message.reply_text(
                "✅ پیام برای مالک ارسال شد."
            )

        except Exception:

            await update.message.reply_text(
                "❌ ارسال پیام ناموفق بود."
            )

        context.user_data.clear()
        return

    # مالک → ادمین
    if state == "contact_admin":

        if not is_owner(user_id):

            context.user_data.clear()
            return

        admin_id = context.user_data.get(
            "contact_admin"
        )

        if admin_id not in admins:

            await update.message.reply_text(
                "❌ این ادمین دیگر فعال نیست."
            )

            context.user_data.clear()
            return

        try:

            await context.bot.send_message(
                admin_id,
                "👑 پیام از طرف مالک\n\n"
                f"💬 {text}"
            )

            await update.message.reply_text(
                "✅ پیام برای ادمین ارسال شد."
            )

        except Exception:

            await update.message.reply_text(
                "❌ ارسال پیام ناموفق بود."
            )

        context.user_data.clear()
        return


# =========================================================


# =========================================================
# 🎮 موتور بازی Neko Room — نسخهٔ بازطراحی‌شده
# =========================================================

GAME_DIR = DATA_DIR / "game_v2"
GAME_DIR.mkdir(parents=True, exist_ok=True)
GAME_PLAYERS_FILE = GAME_DIR / "players.json"
GAME_ITEMS_FILE = GAME_DIR / "items.json"
GAME_RECIPES_FILE = GAME_DIR / "recipes.json"
GAME_MARKET_FILE = GAME_DIR / "market.json"
GAME_ALLIANCES_FILE = GAME_DIR / "alliances.json"
GAME_STATE_FILE = GAME_DIR / "state.json"
GAME_LOG_FILE = GAME_DIR / "log.json"

RARITY_FA = {
    "common": "عادی",
    "uncommon": "غیرمعمول",
    "rare": "کمیاب",
    "epic": "حماسی",
    "legendary": "افسانه‌ای",
    "mythic": "اسطوره‌ای",
    "unique": "منحصربه‌فرد",
}

REGIONS = [
    {"id": "forest", "name": "🌲 جنگل", "level": 1, "sections": ["دره سبز", "خرابه‌های جنگلی", "غار خزه‌ای", "قلب جنگل", "دریاچه جنگلی"]},
    {"id": "desert", "name": "🏜 بیابان", "level": 4, "sections": ["تپه‌های شنی", "دشت نمک", "شهر مدفون", "چاه خشک", "دره ماسه‌ای"]},
    {"id": "frozen", "name": "❄️ منطقه یخ‌زده", "level": 7, "sections": ["دره یخی", "ایستگاه قطبی", "غار یخ", "دریاچه منجمد", "قله یخی"]},
    {"id": "volcanic", "name": "🌋 منطقه آتشفشانی", "level": 10, "sections": ["دامنه آتشفشان", "رود آذرین", "دهانه خاموش", "تونل آذرین", "دشت خاکستر"]},
    {"id": "factory", "name": "🏭 کارخانه متروکه", "level": 14, "sections": ["سالن مونتاژ", "انبار متروک", "خط تولید", "مرکز کنترل", "آزمایشگاه صنعتی"]},
    {"id": "nuclear", "name": "☢️ منطقه هسته‌ای", "level": 20, "sections": ["کمربند هسته‌ای", "پناهگاه شکسته", "راکتور قدیمی", "اتاق آزمایش", "تونل تشعشعی"]},
    {"id": "void", "name": "🌀 منطقه خلأ", "level": 30, "sections": ["مرز خلأ", "شکاف ابعادی", "میدان کوانتومی", "هسته خلأ", "آستانه بی‌نهایت"]},
]

# هر بخش دقیقاً ۱۰ آیتم دارد؛ احتمال‌ها متفاوت و مجموع هر بخش = 100 است.
EXPLORATION_WEIGHTS = [30, 18, 13, 10, 8, 7, 5, 4, 3, 2]
EXPLORATION_MATERIALS = [
    ("آهن خام", "مواد خام", "common", 35, 18),
    ("مس خام", "مواد خام", "common", 42, 22),
    ("زغال فشرده", "مواد خام", "common", 30, 16),
    ("کریستال سیلیکون", "قطعات", "uncommon", 80, 42),
    ("نیکل خالص", "مواد خام", "uncommon", 95, 50),
    ("تیتانیوم کمیاب", "مواد خام", "rare", 150, 82),
    ("کریستال الماس", "مواد خام", "epic", 300, 165),
    ("کریستال انرژی", "انرژی", "epic", 280, 150),
    ("قطعه کوانتومی", "تحقیق", "mythic", 620, 340),
    ("اثر بیگانه", "آثار", "unique", 950, 520),
]

BASE_ITEMS = [
    ("iron_ore", "سنگ آهن", "مواد خام", "common", 20, 12, 2, 1, {}),
    ("copper_ore", "سنگ مس", "مواد خام", "common", 25, 15, 2, 1, {}),
    ("coal", "زغال‌سنگ", "مواد خام", "common", 18, 10, 2, 1, {}),
    ("silver_ore", "سنگ نقره", "مواد خام", "uncommon", 45, 28, 2, 3, {}),
    ("gold_ore", "سنگ طلا", "مواد خام", "rare", 90, 55, 2, 5, {}),
    ("titanium_ore", "سنگ تیتانیوم", "مواد خام", "epic", 150, 95, 2, 7, {}),
    ("lithium_crystal", "کریستال لیتیوم", "انرژی", "rare", 120, 72, 1, 7, {}),
    ("diamond", "الماس", "مواد خام", "epic", 420, 250, 1, 10, {}),
    ("platinum_ore", "سنگ پلاتین", "مواد خام", "legendary", 700, 420, 2, 15, {}),
    ("cobalt_ore", "سنگ کبالت", "مواد خام", "rare", 160, 96, 2, 8, {}),
    ("nickel_ore", "سنگ نیکل", "مواد خام", "uncommon", 120, 72, 2, 6, {}),
    ("quartz", "کوارتز", "مواد خام", "uncommon", 70, 42, 1, 4, {}),
    ("obsidian", "ابسیدین", "مواد خام", "rare", 190, 114, 2, 9, {}),
    ("emerald", "زمرد", "مواد خام", "epic", 500, 300, 1, 14, {}),
    ("ruby", "یاقوت", "مواد خام", "epic", 470, 282, 1, 13, {}),
    ("sapphire", "یاقوت کبود", "مواد خام", "epic", 450, 270, 1, 13, {}),
    ("graphite", "گرافیت", "مواد خام", "uncommon", 90, 54, 1, 5, {}),
    ("tungsten", "تنگستن", "مواد خام", "rare", 230, 138, 2, 11, {}),
    ("iridium", "ایریدیوم", "مواد خام", "legendary", 760, 456, 2, 18, {}),
    ("astral_crystal", "کریستال آسترال", "مواد خام", "mythic", 1100, 660, 1, 25, {}),
    ("amber", "کهربا", "مواد خام", "uncommon", 110, 66, 1, 4, {}),
    ("basalt", "بازالت", "مواد خام", "common", 45, 27, 2, 2, {}),
    ("magnesium", "منیزیم", "مواد خام", "uncommon", 130, 78, 1, 6, {}),
    ("zinc", "روی", "مواد خام", "common", 55, 33, 2, 3, {}),
    ("chromium", "کروم", "مواد خام", "rare", 180, 108, 2, 9, {}),
    ("palladium", "پالادیوم", "مواد خام", "legendary", 680, 408, 2, 17, {}),
    ("meteor_shard", "تکه شهاب‌سنگ", "مواد خام", "mythic", 900, 540, 2, 22, {}),
    ("silicon_crystal", "کریستال سیلیکون", "قطعات", "uncommon", 60, 36, 1, 3, {}),
    ("steel_ingot", "شمش فولاد", "مواد صنعتی", "common", 80, 50, 2, 1, {}),
    ("copper_ingot", "شمش مس", "مواد صنعتی", "common", 75, 45, 2, 1, {}),
    ("gold_ingot", "شمش طلا", "مواد صنعتی", "rare", 180, 110, 2, 5, {}),
    ("titanium_ingot", "شمش تیتانیوم", "مواد صنعتی", "epic", 300, 190, 2, 7, {}),
    ("carbon_fiber", "فیبر کربن", "مواد صنعتی", "rare", 220, 140, 1, 8, {}),
    ("electronic_circuit", "مدار الکترونیکی", "قطعات", "uncommon", 130, 80, 1, 3, {}),
    ("advanced_chip", "چیپ پیشرفته", "قطعات", "rare", 260, 160, 1, 8, {}),
    ("energy_cell", "سلول انرژی", "انرژی", "rare", 300, 180, 1, 8, {}),
    ("power_core", "هسته نیرو", "انرژی", "epic", 600, 360, 2, 12, {}),
    ("research_data", "چیپ داده تحقیق", "تحقیق", "uncommon", 140, 85, 1, 3, {}),
    ("research_module", "ماژول تحقیق", "تحقیق", "rare", 450, 270, 3, 10, {}),
    ("basic_pickaxe", "کلنگ استخراج ساده", "ابزار", "common", 100, 60, 3, 1, {}),
    ("ore_scanner", "اسکنر سنگ معدن", "تجهیزات اکتشافی", "uncommon", 250, 150, 2, 4, {"explore_bonus": 6}),
    ("mining_lamp", "چراغ معدن", "تجهیزات اکتشافی", "common", 80, 48, 1, 1, {"explore_bonus": 4}),
    ("scout_robot", "ربات شناسایی", "تجهیزات اکتشافی", "rare", 650, 390, 5, 10, {"explore_bonus": 10}),
    ("power_drill", "دریل قدرتی", "ابزار", "uncommon", 280, 168, 4, 5, {"extract_quality": 8}),
    ("laser_cutter", "برشگر لیزری", "ابزار", "rare", 520, 312, 3, 12, {"extract_quality": 14}),
    ("mining_robot", "ربات معدن‌کار", "تجهیزات استخراج", "rare", 850, 510, 7, 12, {"extract_quality": 18}),
    ("repair_kit", "کیت تعمیر", "قطعات", "uncommon", 160, 96, 2, 3, {}),
    ("basic_pistol", "تپانچه ساده", "سلاح", "common", 300, 180, 2, 8, {"weapon_power": 18}),
    ("gold_pistol", "تپانچه طلایی", "سلاح", "rare", 900, 540, 3, 10, {"weapon_power": 34}),
    ("assault_rifle", "تفنگ تهاجمی", "سلاح", "uncommon", 650, 390, 4, 12, {"weapon_power": 30}),
    ("plasma_rifle", "تفنگ پلاسما", "سلاح", "epic", 1400, 840, 4, 20, {"weapon_power": 52}),
    ("energy_blade", "تیغه انرژی", "سلاح", "epic", 1300, 780, 3, 20, {"weapon_power": 48}),
    ("plasma_cannon", "توپ پلاسما", "سلاح", "legendary", 2400, 1440, 8, 28, {"weapon_power": 76}),
    ("tactical_helmet", "کلاه تاکتیکی", "زره", "uncommon", 300, 180, 2, 10, {"armor_defense": 12}),
    ("combat_armor", "زره رزمی", "زره", "rare", 900, 540, 8, 15, {"armor_defense": 28}),
    ("energy_shield", "سپر انرژی", "زره", "epic", 1000, 600, 4, 20, {"armor_defense": 40}),
    ("power_armor", "زره قدرتی", "زره", "legendary", 2800, 1680, 12, 28, {"armor_defense": 64}),
    ("assault_drone", "پهپاد تهاجمی", "حمله پایگاه", "epic", 1600, 960, 5, 20, {"base_attack": 40}),
    ("phase_drone", "پهپاد فازی", "حمله پایگاه", "legendary", 3200, 1920, 6, 30, {"base_attack": 75}),
    ("tactical_missile", "موشک تاکتیکی", "حمله پایگاه", "rare", 900, 540, 2, 15, {"missile_power": 38}),
    ("heavy_missile", "موشک سنگین", "حمله پایگاه", "legendary", 1800, 1080, 3, 25, {"missile_power": 72}),
    ("targeting_system", "سامانه هدف‌گیری", "فناوری پایگاه", "rare", 700, 420, 2, 14, {"base_attack": 16}),
    ("command_core", "هسته فرماندهی", "فناوری پایگاه", "epic", 1700, 1020, 4, 18, {"base_attack": 24}),
    ("defense_turret", "برجک دفاعی", "دفاع پایگاه", "uncommon", 650, 390, 8, 5, {"base_defense": 12}),
    ("heavy_turret", "برجک سنگین", "دفاع پایگاه", "rare", 1000, 600, 12, 10, {"base_defense": 24}),
    ("laser_turret", "برجک لیزری", "دفاع پایگاه", "epic", 1500, 900, 10, 15, {"base_defense": 38}),
    ("shield_generator", "مولد سپر", "دفاع پایگاه", "epic", 1400, 840, 8, 15, {"base_defense": 34}),
    ("missile_defense", "سامانه دفاع موشکی", "دفاع پایگاه", "legendary", 2300, 1380, 14, 22, {"base_defense": 52}),
    ("barrier_generator", "مولد سد انرژی", "دفاع پایگاه", "legendary", 3000, 1800, 10, 30, {"base_defense": 70}),
    ("security_drone", "پهپاد امنیتی", "دفاع پایگاه", "rare", 850, 510, 5, 9, {"base_defense": 20}),
    ("solar_panel", "پنل خورشیدی", "انرژی", "uncommon", 240, 145, 4, 3, {"energy_regen": 1}),
    ("energy_turbine", "توربین انرژی", "انرژی", "rare", 420, 250, 5, 8, {"energy_regen": 2}),
    ("thermal_generator", "مولد حرارتی", "انرژی", "rare", 500, 300, 5, 8, {"energy_regen": 2}),
    ("energy_converter", "مبدل انرژی", "انرژی", "epic", 700, 420, 4, 14, {"energy_regen": 3}),
    ("factory_core", "هسته کارخانه", "فناوری کارخانه", "rare", 800, 480, 4, 10, {}),
    ("industrial_furnace", "کوره صنعتی", "ماشین‌آلات", "uncommon", 350, 210, 8, 4, {}),
    ("assembly_machine", "دستگاه مونتاژ", "ماشین‌آلات", "rare", 650, 390, 9, 10, {}),
    ("nanofabricator", "نانوساز", "ماشین‌آلات", "legendary", 1600, 960, 8, 18, {}),
]

LAB_NAMES = [
    "سلول انرژی پایدار", "هسته ذخیره انرژی", "ماژول تحلیل ماده", "پردازشگر تحقیقاتی", "رایانه تحقیقاتی", "چیپ محاسباتی",
    "هسته کوانتومی", "مبدل نانویی", "سنسور دقیق", "کنترلر انرژی", "منبع انرژی فشرده", "هسته شتاب‌دهنده",
    "ماژول میدان", "مولد میدان", "شبکه انرژی هوشمند", "هسته پردازش پیشرفته", "رایانه کوانتومی سبک", "پردازشگر عصبی",
    "هسته هوش مصنوعی", "مبدل هوشمند", "هسته تثبیت‌گر", "داده‌نگار پیشرفته", "ماژول رمزگشایی", "اسکنر چندطیفی",
    "اسکنر کوانتومی", "هسته آزمایشی", "ماده نانو", "کریستال ناپایدار", "کریستال خلأ", "هسته ابعادی",
    "راکتور کوچک", "راکتور فشرده", "هسته همجوشی", "مولد پلاسما", "هسته پلاسما", "مبدل خلأ",
    "کنترلر ابعادی", "دروازه آزمایشی", "هسته کیهانی", "سامانه تحقیق نهایی",
]
WORKSHOP_NAMES = [
    "ماژول تقویت استخراج", "هسته ابزار استخراج", "دریل صنعتی", "اسکنر معدن پیشرفته", "ربات معدن‌کار پیشرفته", "ربات شناسایی پیشرفته",
    "بازوی تعمیرکار", "سامانه تعمیر خودکار", "تپانچه تقویت‌شده", "تفنگ تاکتیکی", "تفنگ پلاسما سبک", "تفنگ پلاسما سنگین",
    "تیغه انرژی پیشرفته", "توپ پلاسما سبک", "توپ پلاسما سنگین", "کلاه تاکتیکی پیشرفته", "زره رزمی پیشرفته", "زره انرژی",
    "زره قدرتی نسل دوم", "سپر انرژی پیشرفته", "سامانه نشانه‌روی", "سامانه کنترل سلاح", "هسته فرماندهی شخصی", "پلتفرم پهپاد",
    "پهپاد تهاجمی سبک", "پهپاد تهاجمی سنگین", "پهپاد فازی", "موشک تاکتیکی اصلاح‌شده", "موشک سنگین اصلاح‌شده", "سامانه پرتاب خودکار",
    "ابزار برش دقیق", "برشگر لیزری صنعتی", "کیت مهندسی میدان", "دستگاه ساخت سریع", "نانوساز کارگاهی", "جعبه ابزار هوشمند",
    "سامانه تعادل نیرو", "ماژول جذب انرژی", "بدنه مقاوم", "تجهیزات کارگاهی نهایی",
]
FACTORY_NAMES = [
    "شمش فولاد تقویت‌شده", "شمش تیتانیوم خالص", "فیبر کربن چندلایه", "مدار صنعتی", "چیپ صنعتی", "سلول انرژی صنعتی",
    "هسته نیرو صنعتی", "ماژول هیدرولیک", "موتور سروو", "شاسی ربات", "کوره صنعتی پیشرفته", "دستگاه مونتاژ پیشرفته",
    "پردازشگر مواد", "پالایشگر صنعتی", "نوار نقاله خودکار", "بازوی رباتیک صنعتی", "دستگاه فشرده‌سازی", "پردازشگر شیمیایی",
    "نانوساز صنعتی", "راکتور صنعتی", "برجک دفاعی تقویت‌شده", "برجک سنگین تقویت‌شده", "برجک لیزری پیشرفته", "مولد سپر پیشرفته",
    "مولد سد انرژی", "سامانه دفاع موشکی پیشرفته", "پهپاد امنیتی پیشرفته", "هسته کنترل دفاع", "سامانه دفاع خودکار", "سامانه دفاع چندلایه",
    "پهپاد شناسایی صنعتی", "پهپاد رزمی کارخانه", "سامانه هدف‌گیری کارخانه", "هسته فرماندهی پایگاه", "موشک کارخانه‌ای", "موشک سنگین کارخانه‌ای",
    "سامانه پرتاب چندگانه", "راکتور کارخانه", "هسته کارخانه هوشمند", "فناوری کارخانه نهایی",
]

EXTRA_OUTPUTS = {
    "tactical_helmet_2": ("کلاه تاکتیکی پیشرفته", "زره", "rare", 600, 3, 14, {"armor_defense": 20}),
    "combat_armor_2": ("زره رزمی پیشرفته", "زره", "epic", 1400, 9, 20, {"armor_defense": 40}),
    "energy_shield_2": ("سپر انرژی پیشرفته", "زره", "legendary", 2200, 5, 26, {"armor_defense": 58}),
    "tactical_gun_2": ("تفنگ تاکتیکی پیشرفته", "سلاح", "rare", 1200, 5, 16, {"weapon_power": 42}),
    "plasma_gun_2": ("تفنگ پلاسما سنگین", "سلاح", "legendary", 2800, 6, 28, {"weapon_power": 82}),
    "golden_core": ("هسته طلایی", "انرژی", "epic", 1500, 4, 16, {}),
    "quantum_core": ("هسته کوانتومی نهایی", "تحقیق", "mythic", 4200, 5, 32, {"base_attack": 18}),
    "base_ai": ("هوش مصنوعی پایگاه", "فناوری پایگاه", "legendary", 3600, 4, 30, {"base_defense": 55, "base_attack": 25}),
    "phase_engine": ("موتور فازی", "فناوری پایگاه", "legendary", 4000, 6, 30, {"base_attack": 35}),
    "diamond_frame": ("بدنه الماسی", "زره", "epic", 2600, 12, 18, {"armor_defense": 52}),
}

GAME_PLAYERS = load_json(GAME_PLAYERS_FILE, {})
GAME_ITEMS = load_json(GAME_ITEMS_FILE, [])
GAME_RECIPES = load_json(GAME_RECIPES_FILE, [])
GAME_MARKET = load_json(GAME_MARKET_FILE, [])
GAME_ALLIANCES = load_json(GAME_ALLIANCES_FILE, {})
GAME_STATE = load_json(GAME_STATE_FILE, {"schema": 2})
GAME_LOG = load_json(GAME_LOG_FILE, [])
if not isinstance(GAME_PLAYERS, dict): GAME_PLAYERS = {}
if not isinstance(GAME_ITEMS, list): GAME_ITEMS = []
if not isinstance(GAME_RECIPES, list): GAME_RECIPES = []
if not isinstance(GAME_MARKET, list): GAME_MARKET = []
if not isinstance(GAME_ALLIANCES, dict): GAME_ALLIANCES = {}

def _game_item_from_row(row):
    iid, name, category, rarity, buy, sell, weight, req, stats = row
    return {
        "id": iid, "name": name, "category": category, "rarity": rarity,
        "base_price": int(buy), "sell_price": int(sell), "weight": int(weight),
        "required_level": int(req), "required_research": 0, "stack_limit": 999,
        "tradable": True, "active": True, "stats": dict(stats), "image_file_id": None,
        "description": f"آیتم کاربردی دستهٔ {category} با درجهٔ {RARITY_FA.get(rarity, rarity)}.",
    }

def _game_add_item(item):
    if not any(str(x.get("id")) == str(item.get("id")) for x in GAME_ITEMS):
        GAME_ITEMS.append(item)

def _game_crafted_item(iid, name, category, rarity, price, weight, req, stats=None):
    return {
        "id": iid, "name": name, "category": category, "rarity": rarity,
        "base_price": int(price), "sell_price": max(1, int(price * 0.62)),
        "weight": int(weight), "required_level": int(req), "required_research": max(0, int(req) // 3),
        "stack_limit": 99, "tradable": True, "active": True, "stats": stats or {},
        "image_file_id": None, "description": f"محصول ساختنی کاربردی: {name}",
    }

def _seed_game_items():
    for row in BASE_ITEMS:
        _game_add_item(_game_item_from_row(row))
    for key, value in EXTRA_OUTPUTS.items():
        name, cat, rarity, price, weight, req, stats = value
        _game_add_item(_game_crafted_item(key, name, cat, rarity, price, weight, req, stats))
    for r_index, region in enumerate(REGIONS, 1):
        for s_index, section in enumerate(region["sections"], 1):
            for n in range(1, 11):
                mat = EXPLORATION_MATERIALS[n - 1]
                iid = f"explore_{r_index}_{s_index}_{n}"
                name = f"{mat[0]} {section} {n}"
                _game_add_item({
                    "id": iid, "name": name, "category": mat[1], "rarity": mat[2],
                    "base_price": mat[3] + r_index * 18 + s_index * 7,
                    "sell_price": mat[4] + r_index * 11 + s_index * 4,
                    "weight": 1 if n >= 7 else 2, "required_level": region["level"],
                    "required_research": max(0, r_index - 2), "stack_limit": 99, "tradable": True,
                    "active": True, "stats": {}, "image_file_id": None,
                    "description": f"یافتهٔ منحصربه‌فرد از {section} در {region['name']}؛ قابل فروش و استفاده در ساخت.",
                })

_seed_game_items()

RECIPE_OUTPUT_SPECS = []
for station, names in (("lab", LAB_NAMES), ("workshop", WORKSHOP_NAMES), ("factory", FACTORY_NAMES)):
    RECIPE_OUTPUT_SPECS.extend((station, i + 1, name) for i, name in enumerate(names))

# نام‌های خروجی ثابت و دقیقاً ۱۲۰ دستور. دستورها تصادفی نیستند و هر بار یکسان ساخته می‌شوند.
def _ensure_recipe_item(counter, station, name, req, rarity):
    low = name.lower()
    if "پلاسما" in name or "تفنگ" in name or "تپانچه" in name:
        cat, stats = "سلاح", {"weapon_power": 20 + counter}
    elif "زره" in name or "کلاه" in name or "سپر" in name or "بدنه" in name:
        cat, stats = "زره", {"armor_defense": 12 + counter}
    elif "برجک" in name or "دفاع" in name or "مولد سپر" in name or "سد" in name:
        cat, stats = "دفاع پایگاه", {"base_defense": 12 + counter}
    elif "پهپاد" in name or "موشک" in name or "پرتاب" in name or "هدف" in name or "فرماندهی پایگاه" in name:
        cat, stats = "حمله پایگاه", {"base_attack": 10 + counter // 2}
        if "موشک" in name: stats["missile_power"] = 20 + counter // 2
    elif "کلنگ" in name or "دریل" in name or "اسکنر معدن" in name or "برشگر" in name:
        cat, stats = "ابزار", {"extract_quality": 5 + counter // 4}
    else:
        cat, stats = {"lab": "تحقیق", "workshop": "ماشین‌آلات", "factory": "مواد صنعتی"}.get(station, "قطعات"), {}
    iid = f"craft_{counter:03d}"
    _game_add_item(_game_crafted_item(iid, name, cat, rarity, 250 + counter * 65, 2 + counter % 8, req, stats))
    return iid

def _seed_game_recipes():
    valid_outputs = set(x.get("id") for x in GAME_ITEMS)
    if len(GAME_RECIPES) == 120 and GAME_STATE.get("schema") == 2 and all(r.get("output_item_id") in valid_outputs for r in GAME_RECIPES):
        return
    GAME_RECIPES.clear()
    material_pool = [
        "iron_ore", "copper_ore", "coal", "silver_ore", "gold_ore", "titanium_ore", "diamond", "platinum_ore", "cobalt_ore", "nickel_ore", "quartz", "obsidian", "emerald", "ruby", "sapphire", "graphite", "tungsten", "iridium", "astral_crystal", "amber", "basalt", "magnesium", "zinc", "chromium", "palladium", "meteor_shard",
        "silicon_crystal", "steel_ingot", "copper_ingot", "gold_ingot", "titanium_ingot", "carbon_fiber",
        "electronic_circuit", "advanced_chip", "energy_cell", "power_core", "research_data", "research_module"
    ]
    # 280 آیتم اکتشافی نیز در مواد دستورها وارد می‌شوند تا آیتم‌های اکتشافی فقط برای فروش نباشند.
    for r in range(1, 121):
        station = "lab" if r <= 40 else "workshop" if r <= 80 else "factory"
        local_index = r if station == "lab" else r - 40 if station == "workshop" else r - 80
        name = (LAB_NAMES + WORKSHOP_NAMES + FACTORY_NAMES)[r - 1]
        req_level = max(1, min(30, 1 + ((r - 1) // 4)))
        req_research = min(10, (r - 1) // 12)
        if r <= 20: rarity = "common"
        elif r <= 45: rarity = "uncommon"
        elif r <= 75: rarity = "rare"
        elif r <= 100: rarity = "epic"
        elif r <= 115: rarity = "legendary"
        else: rarity = "mythic"
        # دستور ویژهٔ آزمایشگاه: شمش طلا + شمش آهن/فولاد → تپانچه طلایی.
        if r == 1:
            output_id = "gold_pistol"
            recipe_name = "تپانچه طلایی"
            ingredients = {"gold_ingot": 1, "steel_ingot": 2, "diamond": 1}
        else:
            output_id = _ensure_recipe_item(r, station, name, req_level, rarity)
            a = material_pool[(r - 1) % len(material_pool)]
            b = material_pool[(r + 5) % len(material_pool)]
            c = f"explore_{((r - 1) % 7) + 1}_{((r + 1) % 5) + 1}_{((r + 2) % 10) + 1}"
            ingredients = {a: 2 + (r % 3), b: 1 + (r % 2), c: 1}
            recipe_name = f"ساخت {name}"
        GAME_RECIPES.append({
            "id": f"r{r:03d}", "name": recipe_name, "station": station,
            "required_level": req_level, "required_research": req_research,
            "ingredients": ingredients, "output_item_id": output_id,
            "output_qty": 1 + (1 if r % 25 == 0 else 0), "xp": 10 + r,
        })
    GAME_STATE["schema"] = 2

_seed_game_recipes()

def game_save():
    save_json(GAME_PLAYERS_FILE, GAME_PLAYERS)
    save_json(GAME_ITEMS_FILE, GAME_ITEMS)
    save_json(GAME_RECIPES_FILE, GAME_RECIPES)
    save_json(GAME_MARKET_FILE, GAME_MARKET)
    save_json(GAME_ALLIANCES_FILE, GAME_ALLIANCES)
    save_json(GAME_STATE_FILE, GAME_STATE)
    save_json(GAME_LOG_FILE, GAME_LOG[-5000:])

def game_log(action, user_id=0, details=""):
    GAME_LOG.append({"time": now(), "action": action, "user_id": int(user_id), "details": details})
    del GAME_LOG[:-5000]

def game_item(item_id):
    return next((x for x in GAME_ITEMS if str(x.get("id")) == str(item_id) and x.get("active", True)), None)

def _default_game_player(user):
    return {
        "id": int(user.id), "name": user.full_name or user.first_name or "بازیکن", "username": user.username,
        "level": 1, "xp": 0, "money": 500, "energy": 100, "max_energy": 100,
        "health": 100, "max_health": 100, "base_level": 1, "research_level": 0, "pickaxe_level": 1,
        "inventory": {"basic_pickaxe": 1}, "capacity_base": 100,
        "equipped_weapon": None, "equipped_armor": None, "bodyguard_level": 0, "installed_defense": {},
        "last_extract_at": 0.0, "last_energy_sync": time.time(), "protected_until": 0.0,
        "wins": 0, "losses": 0, "base_wins": 0, "base_losses": 0,
        "daily_date": "", "daily_claimed": False,
        "daily_quests": {"extract": 0, "explore": 0, "personal_attack": 0, "base_attack": 0, "reward_claimed": False},
        "alliance_id": None,
    }

def game_sync(p):
    ts = time.time()
    last = float(p.get("last_energy_sync", ts))
    minutes = int(max(0, ts - last) // 60)
    if minutes:
        regen_bonus = 0
        for iid, qty in p.get("inventory", {}).items():
            it = game_item(iid)
            if it:
                regen_bonus += int(it.get("stats", {}).get("energy_regen", 0)) * min(3, int(qty))
        p["energy"] = min(int(p.get("max_energy", 100)), int(p.get("energy", 0)) + minutes * (1 + regen_bonus))
        p["last_energy_sync"] = ts
    today = datetime.now().strftime("%Y-%m-%d")
    if p.get("daily_date") != today:
        p["daily_date"] = today
        p["daily_claimed"] = False
        p["daily_quests"] = {"extract": 0, "explore": 0, "personal_attack": 0, "base_attack": 0, "reward_claimed": False}
    if p.get("protected_until", 0) and ts >= float(p["protected_until"]):
        p["protected_until"] = 0
        p["health"] = p.get("max_health", 100)

def game_player(user):
    uid = str(user.id)
    p = GAME_PLAYERS.get(uid)
    if not isinstance(p, dict):
        p = _default_game_player(user)
        GAME_PLAYERS[uid] = p
    else:
        defaults = _default_game_player(user)
        for k, v in defaults.items():
            if k not in p:
                p[k] = v
        p["name"] = user.full_name or user.first_name or p.get("name", "بازیکن")
        p["username"] = user.username
        if not isinstance(p.get("inventory"), dict): p["inventory"] = {"basic_pickaxe": 1}
        if not isinstance(p.get("installed_defense"), dict): p["installed_defense"] = {}
    game_sync(p)
    game_save()
    return p

def game_weight(p):
    total = 0
    for iid, qty in p.get("inventory", {}).items():
        it = game_item(iid)
        if it: total += int(it.get("weight", 1)) * max(0, int(qty))
    return total

def game_capacity(p):
    return int(p.get("capacity_base", 100)) + max(0, int(p.get("base_level", 1)) - 1) * 25

def game_has(p, iid, qty=1):
    return int(p.get("inventory", {}).get(iid, 0)) >= int(qty)

def game_can_add(p, iid, qty=1):
    it = game_item(iid)
    if not it or qty <= 0: return False
    current = int(p.get("inventory", {}).get(iid, 0))
    if current + qty > int(it.get("stack_limit", 999)): return False
    return game_weight(p) + int(it.get("weight", 1)) * qty <= game_capacity(p)

def game_add(p, iid, qty=1):
    if not game_can_add(p, iid, qty): return False
    p.setdefault("inventory", {})[iid] = int(p["inventory"].get(iid, 0)) + int(qty)
    return True

def game_remove(p, iid, qty=1):
    cur = int(p.get("inventory", {}).get(iid, 0))
    if qty <= 0 or cur < qty: return False
    if cur == qty: p["inventory"].pop(iid, None)
    else: p["inventory"][iid] = cur - qty
    return True

def game_xp(p, amount):
    p["xp"] = int(p.get("xp", 0)) + int(amount)
    leveled = False
    while int(p.get("level", 1)) < 50 and p["xp"] >= int(p["level"]) * 100:
        p["xp"] -= int(p["level"]) * 100
        p["level"] += 1
        p["max_energy"] = 100 + (p["level"] - 1) * 3
        p["max_health"] = 100 + (p["level"] - 1) * 2
        p["energy"] = p["max_energy"]
        p["health"] = p["max_health"]
        leveled = True
    return leveled

def game_protected(p):
    return float(p.get("protected_until", 0)) > time.time()

def game_remaining_protection(p):
    return max(0, int(float(p.get("protected_until", 0)) - time.time()))

def game_personal_defense(p):
    score = 5 + int(p.get("level", 1)) * 2 + int(p.get("bodyguard_level", 0)) * 8
    armor = game_item(p.get("equipped_armor"))
    if armor: score += int(armor.get("stats", {}).get("armor_defense", 0))
    return score

def game_personal_attack_power(p):
    score = 10 + int(p.get("level", 1)) * 3
    weapon = game_item(p.get("equipped_weapon"))
    if weapon: score += int(weapon.get("stats", {}).get("weapon_power", 0))
    return score

def game_base_defense(p):
    score = int(p.get("base_level", 1)) * 12
    for iid, qty in p.get("installed_defense", {}).items():
        it = game_item(iid)
        if it: score += int(it.get("stats", {}).get("base_defense", 0)) * int(qty)
    return score

def game_base_attack_power(p):
    score = int(p.get("base_level", 1)) * 8
    for iid, qty in p.get("inventory", {}).items():
        it = game_item(iid)
        if it: score += int(it.get("stats", {}).get("base_attack", 0)) * min(3, int(qty))
    return score

def game_explore_bonus(p):
    bonus = 0
    for iid, qty in p.get("inventory", {}).items():
        if int(qty) <= 0: continue
        it = game_item(iid)
        if it: bonus += int(it.get("stats", {}).get("explore_bonus", 0))
    return min(30, bonus)

def game_group(update):
    chat = update.effective_chat
    return bool(chat and chat.type in (ChatType.GROUP, ChatType.SUPERGROUP))

def game_private(update):
    chat = update.effective_chat
    return bool(chat and chat.type == ChatType.PRIVATE)

def game_cb(uid, action, *args):
    raw = ":".join(["ng", str(uid), action, *[str(x) for x in args]])
    if len(raw.encode("utf-8")) > 64:
        raise ValueError("دادهٔ دکمه بیش از حد طولانی است.")
    return raw

def game_guard_callback(update):
    q = update.callback_query
    if not q: return False
    parts = (q.data or "").split(":")
    if len(parts) < 3 or parts[0] != "ng": return False
    try: owner = int(parts[1])
    except ValueError: owner = -1
    if q.from_user.id != owner or not q.message or q.message.chat.type != ChatType.PRIVATE:
        try: asyncio.create_task(q.answer("❌ این پنل برای شما نیست.", show_alert=True))
        except Exception: pass
        return False
    return True

GAME_HELP = (
    "❓ راهنمای Neko Room\n\n"
    "🎮 بازی در هر گروهی که ربات داخل آن باشد قابل استفاده است.\n"
    "🔐 پنل شخصی فقط در خصوصی ربات باز می‌شود.\n"
    "⛏ استخراج: هر ۵ دقیقه یک‌بار؛ سطح کلنگ فقط مقدار و کیفیت نتیجه را تغییر می‌دهد.\n"
    "🗺 کاوش: ۷ منطقه، ۲۸ بخش و در هر بخش دقیقاً ۱۰ یافتهٔ منحصربه‌فرد دارد.\n"
    "🧪 آزمایشگاه، 🔧 کارگاه و 🏭 کارخانه فقط دستورهای آزادشده را نشان می‌دهند.\n"
    "⚔️ حمله شخصی از سطح ۸ و 🚀 حمله پایگاه از سطح ۲۰ فعال می‌شوند.\n"
    "🛡 با رسیدن سلامت به صفر، ۳۰ دقیقه محافظت فعال می‌شود.\n"
    "🤝 اتحاد و 🛒 بازار بین بازیکنان مستقل هستند.\n\n"
    "میانبر گروه: «بازی»، «انبار»، «راهنما»، «استخراج»، «کاوش» و «پنل خصوصی»."
)

PANEL_LEVELS = {
    "lab": 5, "workshop": 10, "factory": 15, "research": 3,
    "equipment": 2, "base": 1, "personal_attack": 8, "base_attack": 20,
    "market": 3, "quests": 1, "daily": 1, "alliance": 5,
}

def game_panel_unlocked(p, action):
    return int(p.get("level", 1)) >= PANEL_LEVELS.get(action, 1)

def game_locked_text(action):
    return f"🔒 این پنل از سطح {PANEL_LEVELS.get(action, 1)} باز می‌شود."

def game_player_by_id(uid):
    return GAME_PLAYERS.get(str(uid), GAME_PLAYERS.get(uid, {}))

def game_main_keyboard(uid):
    p = game_player_by_id(uid) if "game_player_by_id" in globals() else GAME_PLAYERS.get(str(uid), GAME_PLAYERS.get(uid, {}))
    rows = [
        [InlineKeyboardButton("👤 پروفایل", callback_data=game_cb(uid, "profile")), InlineKeyboardButton("🎒 انبار", callback_data=game_cb(uid, "inventory"))],
        [InlineKeyboardButton("🗺 کاوش", callback_data=game_cb(uid, "explore"))],
    ]
    for a, b in (("lab", "workshop"), ("factory", "research"), ("equipment", "base"), ("personal_attack", "base_attack"), ("market", "quests"), ("daily", "alliance")):
        row=[]
        for action, label in ((a, {"lab":"🧪 آزمایشگاه","factory":"🏭 کارخانه","workshop":"🔧 کارگاه","research":"🔬 تحقیق","equipment":"🛡 تجهیزات","base":"🏠 پایگاه","personal_attack":"⚔️ حمله شخصی","base_attack":"🚀 حمله پایگاه","market":"🛒 بازار","quests":"📜 مأموریت‌ها","daily":"🎁 پاداش روزانه","alliance":"🤝 اتحاد"}[a]), (b, {"lab":"🧪 آزمایشگاه","factory":"🏭 کارخانه","workshop":"🔧 کارگاه","research":"🔬 تحقیق","equipment":"🛡 تجهیزات","base":"🏠 پایگاه","personal_attack":"⚔️ حمله شخصی","base_attack":"🚀 حمله پایگاه","market":"🛒 بازار","quests":"📜 مأموریت‌ها","daily":"🎁 پاداش روزانه","alliance":"🤝 اتحاد"}[b])):
            if game_panel_unlocked(p, action): row.append(InlineKeyboardButton(label, callback_data=game_cb(uid, action, 1) if action in ("lab","workshop","factory") else game_cb(uid, action)))
        if row: rows.append(row)
    rows += [[InlineKeyboardButton("❓ راهنما", callback_data=game_cb(uid, "help"))], [InlineKeyboardButton("❌ بستن", callback_data=game_cb(uid, "close"))]]
    return InlineKeyboardMarkup(rows)

def game_profile_text(p):
    protect = "✅ فعال" if game_protected(p) else "❌ ندارد"
    return (
        "👤 پروفایل بازیکن\n\n"
        f"📛 نام: {p.get('name', 'بازیکن')}\n"
        f"⭐ سطح: {p.get('level', 1)} | تجربه: {p.get('xp', 0)}\n"
        f"💰 پول: {p.get('money', 0):,}\n"
        f"⚡ انرژی: {p.get('energy', 0)}/{p.get('max_energy', 100)}\n"
        f"❤️ سلامت: {p.get('health', 0)}/{p.get('max_health', 100)}\n"
        f"⛏ کلنگ: {p.get('pickaxe_level', 1)}/10\n"
        f"🔬 تحقیق: {p.get('research_level', 0)}/10\n"
        f"⚔️ قدرت شخصی: {game_personal_attack_power(p)}\n"
        f"🛡 دفاع شخصی: {game_personal_defense(p)}\n"
        f"🏠 پایگاه: {p.get('base_level', 1)}/20\n"
        f"👤 نگهبان: {p.get('bodyguard_level', 0)}\n"
        f"🛡 محافظت: {protect}"
    )

async def game_send_private_entry(update, context):
    user = update.effective_user
    bot = await context.bot.get_me()
    username = bot.username
    if not username:
        await update.effective_message.reply_text("❌ لینک خصوصی ربات در دسترس نیست؛ ربات را در خصوصی با /start باز کن.")
        return
    url = f"https://t.me/{username}?start=game"
    await update.effective_message.reply_text(
        "🎮 بازی Neko Room\n\nبرای پنل شخصی بازی روی دکمهٔ زیر بزن:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔐 باز کردن پنل خصوصی", url=url)]])
    )

async def game_start(update, context):
    user = update.effective_user
    if not user or not update.effective_message: return
    if not game_group(update):
        await update.effective_message.reply_text("🎮 بازی Neko Room فقط داخل گروه قابل استفاده است.")
        return
    p = game_player(user)
    await update.effective_message.reply_text(game_profile_text(p), reply_markup=game_main_keyboard(user.id))

async def game_inventory_private(p, update, page=1):
    uid = p["id"]
    items = [(iid, int(q)) for iid, q in p.get("inventory", {}).items() if int(q) > 0 and game_item(iid)]
    items.sort(key=lambda x: game_item(x[0])["name"])
    page = max(1, int(page))
    chunk = items[(page - 1) * 12: page * 12]
    rows = []
    for iid, qty in chunk:
        it = game_item(iid)
        rows.append([InlineKeyboardButton(f"{it['name']} ×{qty}", callback_data=game_cb(uid, "item", iid))])
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️", callback_data=game_cb(uid, "inventory", page - 1)))
    if page * 12 < len(items): nav.append(InlineKeyboardButton("➡️", callback_data=game_cb(uid, "inventory", page + 1)))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ منوی بازی", callback_data=game_cb(uid, "menu"))])
    await update.callback_query.message.edit_text(
        f"🎒 انبار\n\n⚖️ وزن: {game_weight(p)}/{game_capacity(p)}\n📦 آیتم‌ها: {len(items)}\nصفحه: {page}",
        reply_markup=InlineKeyboardMarkup(rows)
    )

async def game_item_detail(p, update, iid):
    q = update.callback_query
    it = game_item(iid)
    if not it:
        await q.message.edit_text("❌ آیتم پیدا نشد.")
        return
    qty = int(p.get("inventory", {}).get(iid, 0))
    text = (f"📦 {it['name']}\n\n📂 دسته: {it['category']}\n"
            f"💎 درجه: {RARITY_FA.get(it['rarity'], it['rarity'])}\n"
            f"⚖️ وزن: {it['weight']}\n💰 قیمت پایه: {it['base_price']:,}\n"
            f"📦 تعداد: {qty}\n📝 {it.get('description','')}")
    await q.message.edit_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ انبار", callback_data=game_cb(p['id'], "inventory"))]]))

async def context_send_photo(update, file_id, caption=""):
    q = update.callback_query
    if q and q.message:
        await q.get_bot().send_photo(q.message.chat.id, file_id, caption=caption or None)

async def game_inventory_command(update, context):
    user = update.effective_user
    if not user: return
    p = game_player(user)
    if game_group(update):
        inv = [(game_item(iid)["name"], int(q)) for iid, q in p["inventory"].items() if int(q) > 0 and game_item(iid)]
        inv.sort()
        lines = ["🎒 انبار شخصی", f"⚖️ وزن: {game_weight(p)}/{game_capacity(p)}", ""] + [f"• {n} ×{q}" for n, q in inv[:20]]
        if len(inv) > 20: lines.append(f"• ... و {len(inv)-20} آیتم دیگر")
        if not inv: lines.append("• انبار خالی است.")
        bot = await context.bot.get_me()
        rows = []
        if bot.username:
            rows = [[InlineKeyboardButton("🔐 باز کردن پنل خصوصی", url=f"https://t.me/{bot.username}?start=game")]]
        await update.effective_message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows) if rows else None)
        return
    # /inventory in private opens the real panel.
    class _Fake: pass
    if update.callback_query:
        await game_inventory_private(p, update, 1)
    else:
        await update.effective_message.reply_text(game_profile_text(p), reply_markup=game_main_keyboard(user.id))

async def game_help_command(update, context):
    await update.effective_message.reply_text(GAME_HELP)

async def game_extract(update, user):
    if not game_group(update):
        await update.effective_message.reply_text("⛏ استخراج فقط به‌صورت گروهی اجرا می‌شود.")
        return
    p = game_player(user)
    remain = 300 - int(time.time() - float(p.get("last_extract_at", 0)))
    if remain > 0:
        await update.effective_message.reply_text(f"⏳ تا استخراج بعدی {remain // 60} دقیقه و {remain % 60} ثانیه باقی مانده است.")
        return
    if int(p.get("energy", 0)) < 10:
        await update.effective_message.reply_text("⚡ انرژی کافی نیست. با گذشت زمان انرژی بازیابی می‌شود.")
        return
    lvl = int(p.get("pickaxe_level", 1))
    quality = int(p.get("extract_quality_bonus", 0))
    raw_pool = ["iron_ore", "copper_ore", "coal", "silver_ore", "gold_ore", "titanium_ore", "lithium_crystal", "diamond", "platinum_ore", "cobalt_ore", "nickel_ore", "quartz", "obsidian", "emerald", "ruby", "sapphire", "graphite", "tungsten", "iridium", "astral_crystal", "amber", "basalt", "magnesium", "zinc", "chromium", "palladium", "meteor_shard"]
    weights = [34,25,18,10,6,4,3,2,2,2,2,2,2,1.7,1.6,1.5,1.4,1.3,1.2,1.1,1,1,0.9,0.8,0.7,0.6,0.5]
    boost=min(10,lvl-1)
    for i in range(len(weights)):
        if i >= 4: weights[i] += boost * 0.12
    iid = random.choices(raw_pool, weights=weights, k=1)[0]
    qty = random.randint(1, 2) + (1 if lvl >= 5 and random.random() < 0.25 else 0) + (1 if lvl >= 8 and random.random() < 0.15 else 0)
    if not game_can_add(p, iid, qty):
        await update.effective_message.reply_text("📦 ظرفیت انبار کافی نیست؛ ابتدا انبار را خالی کن. در این حالت زمان استخراج و انرژی مصرف نمی‌شود.")
        return
    p["energy"] -= 10
    p["last_extract_at"] = time.time()
    game_add(p, iid, qty)
    cash = 8 + lvl * 2
    p["money"] += cash
    p["daily_quests"]["extract"] = min(3, int(p["daily_quests"].get("extract", 0)) + 1)
    before = p["level"]
    game_xp(p, 12 + lvl)
    game_log("extract", p["id"], iid)
    game_save()
    lvl_text = f"\n⬆️ سطح جدید: {p['level']}" if p["level"] > before else ""
    it = game_item(iid)
    await update.effective_message.reply_text(
        f"⛏ استخراج انجام شد.\n\n📦 {it['name']} ×{qty}\n💰 +{cash:,} پول\n⭐ +{12 + lvl} تجربه\n"
        f"⚡ انرژی: {p['energy']}/{p['max_energy']}\n⏱ استخراج بعدی: ۵ دقیقه دیگر.{lvl_text}"
    )

def exploration_chance(p, ri, si):
    base = 38 + ri * 4 + si * 2
    return min(85, base + game_explore_bonus(p) + min(8, int(p["level"]) // 5))

def exploration_items(ri, si):
    return [game_item(f"explore_{ri}_{si}_{n}") for n in range(1, 11)]

async def game_explore_menu(p, update):
    uid = p["id"]
    rows = []
    for i, r in enumerate(REGIONS, 1):
        if p["level"] >= r["level"]:
            rows.append([InlineKeyboardButton(f"{r['name']} | سطح {r['level']}", callback_data=game_cb(uid, "sections", i))])
        else:
            rows.append([InlineKeyboardButton(f"🔒 {r['name']} | سطح {r['level']}", callback_data=game_cb(uid, "locked"))])
    rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid, "menu"))])
    await update.callback_query.message.edit_text("🗺 کاوش\n\nقبل از ورود به هر بخش، شانس کشف آن نمایش داده می‌شود.", reply_markup=InlineKeyboardMarkup(rows))

async def game_sections(p, update, ri):
    uid = p["id"]
    try: r = REGIONS[int(ri)-1]
    except (ValueError, IndexError): return
    if p["level"] < r["level"]:
        await update.callback_query.message.edit_text("🔒 این منطقه هنوز باز نشده است."); return
    rows = []
    for si, sec in enumerate(r["sections"], 1):
        rows.append([InlineKeyboardButton(f"📍 {sec} | شانس کشف {exploration_chance(p, int(ri), si)}٪", callback_data=game_cb(uid, "section", ri, si))])
    rows.append([InlineKeyboardButton("⬅️ مناطق", callback_data=game_cb(uid, "explore"))])
    await update.callback_query.message.edit_text(f"{r['name']}\n\nسطح لازم: {r['level']}", reply_markup=InlineKeyboardMarkup(rows))

async def game_section_preview(p, update, ri, si):
    try: r = REGIONS[int(ri)-1]; sec = r["sections"][int(si)-1]
    except (ValueError, IndexError): return
    items = exploration_items(int(ri), int(si))
    chance = exploration_chance(p, int(ri), int(si))
    lines = [f"📍 {sec}", "", f"🎯 شانس کلی پیدا کردن آیتم: {chance:.1f}٪", "", "احتمال واقعی هر آیتم در هر کاوش:"]
    for it, w in zip(items, EXPLORATION_WEIGHTS):
        actual = chance * float(w) / 100.0
        lines.append(f"• {it['name']} — {actual:.2f}٪")
    lines.append(f"• ❌ بدون آیتم — {100.0-chance:.1f}٪")
    rows = [
        [InlineKeyboardButton("🧭 شروع کاوش", callback_data=game_cb(p['id'], "run_explore", ri, si))],
        [InlineKeyboardButton("⬅️ بخش‌ها", callback_data=game_cb(p['id'], "sections", ri))],
    ]
    await update.callback_query.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))

async def game_run_explore(p, update, ri, si):
    q = update.callback_query
    try: r = REGIONS[int(ri)-1]; sec = r["sections"][int(si)-1]
    except (ValueError, IndexError):
        await q.message.edit_text("❌ بخش نامعتبر است."); return
    if p["level"] < r["level"]:
        await q.message.edit_text("🔒 سطح کافی نیست."); return
    if p["energy"] < 15:
        await q.message.edit_text("⚡ برای کاوش ۱۵ انرژی لازم است."); return
    p["energy"] -= 15
    p["daily_quests"]["explore"] = min(2, int(p["daily_quests"].get("explore", 0)) + 1)
    chance = exploration_chance(p, int(ri), int(si))
    items = exploration_items(int(ri), int(si))
    effective_weights = [chance * float(w) / 100.0 for w in EXPLORATION_WEIGHTS]
    no_item_weight = max(0.0, 100.0 - chance)
    outcome = random.choices(items + [None], weights=effective_weights + [no_item_weight], k=1)[0]
    if outcome is not None:
        it = outcome
        qty = 1 if it["rarity"] in ("legendary", "mythic", "unique") else random.randint(1, 2)
        if game_add(p, it["id"], qty):
            reward = 20 + int(ri) * 15
            p["money"] += reward
            game_xp(p, 24 + int(ri) * 3)
            result = f"✅ {it['name']} ×{qty} پیدا شد.\n💰 +{reward:,} پول"
        else:
            cash = 70 + int(ri) * 20
            p["money"] += cash
            game_xp(p, 15)
            result = f"📦 یافته پیدا شد ولی انبار جا نداشت؛ 💰 +{cash:,} پول جایگزین شد."
    else:
        p["money"] += 10 + int(ri) * 4
        game_xp(p, 10 + int(ri))
        result = "🔎 این بار یافته‌ای به دست نیامد؛ تجربه و درآمد پایه دریافت شد."
    game_log("explore", p["id"], f"{ri}:{si}")
    game_save()
    await q.message.edit_text(f"🗺 نتیجهٔ کاوش در «{sec}»\n\n{result}\n⚡ انرژی: {p['energy']}/{p['max_energy']}")

def recipe_unlocked(p, recipe):
    return int(p["level"]) >= int(recipe["required_level"]) and int(p["research_level"]) >= int(recipe["required_research"])

def recipe_ingredients_text(recipe):
    parts = []
    for iid, qty in recipe["ingredients"].items():
        it = game_item(iid); parts.append(f"{it['name'] if it else iid} ×{qty}")
    return "، ".join(parts)

async def game_recipes(p, update, station, page=1):
    q = update.callback_query
    unlocked = [r for r in GAME_RECIPES if r["station"] == station and recipe_unlocked(p, r)]
    page = max(1, int(page)); chunk = unlocked[(page-1)*8:page*8]
    label = {"lab":"🧪 آزمایشگاه", "workshop":"🔧 کارگاه", "factory":"🏭 کارخانه"}.get(station, station)
    rows = [[InlineKeyboardButton(f"🔧 {r['name']}", callback_data=game_cb(p['id'], "craft", r['id']))] for r in chunk]
    nav = []
    if page > 1: nav.append(InlineKeyboardButton("⬅️", callback_data=game_cb(p['id'], station, page-1)))
    if page * 8 < len(unlocked): nav.append(InlineKeyboardButton("➡️", callback_data=game_cb(p['id'], station, page+1)))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(p['id'], "menu"))])
    await q.message.edit_text(f"{label}\n\n✅ دستورهای آزاد: {len(unlocked)}\n🔒 دستورهای آینده پنهان: {sum(1 for r in GAME_RECIPES if r['station']==station and not recipe_unlocked(p,r))}\nصفحه: {page}", reply_markup=InlineKeyboardMarkup(rows))

async def game_craft(p, update, recipe_id):
    q = update.callback_query
    recipe = next((r for r in GAME_RECIPES if r["id"] == recipe_id), None)
    if not recipe:
        await q.message.edit_text("❌ دستور ساخت پیدا نشد."); return
    if not recipe_unlocked(p, recipe):
        await q.message.edit_text("🔒 این دستور هنوز آزاد نشده است."); return
    for iid, qty in recipe["ingredients"].items():
        if not game_has(p, iid, qty):
            it = game_item(iid); await q.message.edit_text(f"❌ مواد کافی نیست: {it['name'] if it else iid} ×{qty}"); return
    out = game_item(recipe["output_item_id"])
    if not out:
        await q.message.edit_text("❌ خروجی دستور موجود نیست."); return
    if not game_can_add(p, out["id"], int(recipe["output_qty"])):
        await q.message.edit_text("📦 ظرفیت انبار برای خروجی کافی نیست."); return
    for iid, qty in recipe["ingredients"].items(): game_remove(p, iid, qty)
    game_add(p, out["id"], recipe["output_qty"])
    game_xp(p, recipe["xp"])
    game_log("craft", p["id"], recipe_id); game_save()
    await q.message.edit_text(f"✅ ساخته شد: {out['name']} ×{recipe['output_qty']}\n⭐ +{recipe['xp']} تجربه")

async def game_research(p, update):
    q = update.callback_query
    lvl = int(p["research_level"])
    if lvl >= 10:
        await q.message.edit_text("🔬 سطح تحقیق به ۱۰ رسیده است."); return
    nxt = lvl + 1; cost = 600 * nxt; chips = 3 * nxt
    if p["money"] < cost or not game_has(p, "research_data", chips):
        await q.message.edit_text(f"❌ برای تحقیق سطح {nxt}: 💰 {cost:,} پول و 🧪 {chips} چیپ داده تحقیق لازم است."); return
    p["money"] -= cost; game_remove(p, "research_data", chips); p["research_level"] = nxt; game_xp(p, 30); game_save()
    await q.message.edit_text(f"✅ سطح تحقیق به {nxt} رسید؛ دستورهای بیشتری آزاد شدند.")

async def game_equipment(p, update):
    uid = p["id"]; rows = []
    text = (f"🛡 تجهیزات شخصی\n\n⚔️ سلاح: {game_item(p.get('equipped_weapon'))['name'] if game_item(p.get('equipped_weapon')) else 'ندارد'}\n"
            f"🛡 زره: {game_item(p.get('equipped_armor'))['name'] if game_item(p.get('equipped_armor')) else 'ندارد'}\n"
            f"👤 نگهبان: {p.get('bodyguard_level',0)}/{min(10, p['level']//5)}")
    for iid, qty in p["inventory"].items():
        if qty <= 0: continue
        it = game_item(iid)
        if not it: continue
        if it["category"] == "سلاح": rows.append([InlineKeyboardButton(("✅ " if p.get("equipped_weapon") == iid else "⚔️ ") + it["name"], callback_data=game_cb(uid, "equipw", iid))])
        elif it["category"] == "زره": rows.append([InlineKeyboardButton(("✅ " if p.get("equipped_armor") == iid else "🛡 ") + it["name"], callback_data=game_cb(uid, "equipa", iid))])
    rows += [[InlineKeyboardButton("👤 ارتقای نگهبان", callback_data=game_cb(uid, "guard"))], [InlineKeyboardButton("⛏ ارتقای کلنگ", callback_data=game_cb(uid, "pickaxe"))], [InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid, "menu"))]]
    await update.callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows))

async def game_equip(p, update, kind, iid):
    q = update.callback_query; it = game_item(iid)
    if not it or not game_has(p, iid, 1): await q.message.edit_text("❌ این آیتم در انبار نیست."); return
    if kind == "weapon" and it["category"] != "سلاح": await q.message.edit_text("❌ این آیتم سلاح نیست."); return
    if kind == "armor" and it["category"] != "زره": await q.message.edit_text("❌ این آیتم زره نیست."); return
    p["equipped_weapon" if kind == "weapon" else "equipped_armor"] = iid
    game_save(); await q.message.edit_text(f"✅ {it['name']} مجهز شد.")

async def game_guard_upgrade(p, update):
    q = update.callback_query; cur = int(p.get("bodyguard_level",0)); maximum = min(10, int(p["level"]) // 5)
    if maximum <= cur: await q.message.edit_text(f"🔒 حداکثر سطح نگهبان فعلی: {maximum}. برای افزایش آن سطح بازیکن را بالا ببر."); return
    nxt = cur + 1; cost = 1000 * nxt
    if p["money"] < cost: await q.message.edit_text(f"❌ برای نگهبان سطح {nxt} به {cost:,} پول نیاز داری."); return
    p["money"] -= cost; p["bodyguard_level"] = nxt; game_save(); await q.message.edit_text(f"✅ نگهبان به سطح {nxt} رسید.")

async def game_pickaxe_upgrade(p, update):
    q = update.callback_query; cur = int(p.get("pickaxe_level",1))
    if cur >= 10: await q.message.edit_text("⛏ کلنگ به سطح ۱۰ رسیده است."); return
    nxt = cur + 1; money = 300 * nxt; iron = 5 * nxt
    if p["money"] < money or not game_has(p, "iron_ore", iron):
        await q.message.edit_text(f"❌ برای سطح {nxt}: 💰 {money:,} پول و ⛏ {iron} سنگ آهن لازم است."); return
    p["money"] -= money; game_remove(p, "iron_ore", iron); p["pickaxe_level"] = nxt; game_save()
    await q.message.edit_text(f"✅ کلنگ به سطح {nxt} رسید.\n⏱ زمان استخراج همچنان دقیقاً ۵ دقیقه است؛ سطح کلنگ فقط نتیجه را بهتر می‌کند.")

async def game_base(p, update):
    q = update.callback_query; uid = p["id"]
    lines = [f"🏠 پایگاه سطح {p['base_level']}/20", f"🛡 دفاع پایگاه: {game_base_defense(p)}", f"📦 ظرفیت انبار: {game_capacity(p)}", "", "دفاع نصب‌شده:"]
    if p.get("installed_defense"):
        for iid, qty in p["installed_defense"].items():
            it = game_item(iid)
            if it: lines.append(f"• {it['name']} ×{qty}")
    else: lines.append("• هیچ دفاعی نصب نشده است.")
    rows = [[InlineKeyboardButton("➕ نصب دفاع", callback_data=game_cb(uid, "binstmenu"))], [InlineKeyboardButton("➖ حذف دفاع", callback_data=game_cb(uid, "bremmenu"))], [InlineKeyboardButton("⬆️ ارتقای پایگاه", callback_data=game_cb(uid, "bup"))], [InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid, "menu"))]]
    await q.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(rows))

async def game_base_defense_menu(p, update, remove=False):
    q = update.callback_query; uid = p["id"]; rows = []
    for iid, qty in p["inventory"].items():
        it = game_item(iid)
        if not it or it["category"] != "دفاع پایگاه" or qty <= 0: continue
        installed = int(p.get("installed_defense",{}).get(iid,0))
        if remove and installed > 0: rows.append([InlineKeyboardButton(f"➖ {it['name']} | نصب {installed}", callback_data=game_cb(uid,"brem",iid))])
        elif not remove and int(qty) - installed > 0: rows.append([InlineKeyboardButton(f"➕ {it['name']} | موجود {int(qty)-installed}", callback_data=game_cb(uid,"binst",iid))])
    if not rows: rows.append([InlineKeyboardButton("ℹ️ موردی وجود ندارد", callback_data=game_cb(uid,"noop"))])
    rows.append([InlineKeyboardButton("⬅️ پایگاه", callback_data=game_cb(uid,"base"))])
    await q.message.edit_text("دفاع موردنظر را انتخاب کن:", reply_markup=InlineKeyboardMarkup(rows))

async def game_base_install(p, update, iid):
    q = update.callback_query; it = game_item(iid)
    if not it or it["category"] != "دفاع پایگاه" or not game_has(p,iid,1): await q.message.edit_text("❌ آیتم دفاعی معتبر نیست."); return
    installed = int(p.setdefault("installed_defense",{}).get(iid,0))
    if int(p["inventory"].get(iid,0)) <= installed: await q.message.edit_text("❌ از این آیتم دفاعیِ آزاد چیزی باقی نمانده است."); return
    p["inventory"][iid] = int(p["inventory"][iid]) - 1
    if p["inventory"][iid] <= 0: p["inventory"].pop(iid,None)
    p["installed_defense"][iid] = installed + 1
    game_save(); await q.message.edit_text(f"✅ {it['name']} در پایگاه نصب شد.")

async def game_base_remove(p, update, iid):
    q = update.callback_query; installed = int(p.setdefault("installed_defense",{}).get(iid,0)); it = game_item(iid)
    if installed <= 0: await q.message.edit_text("❌ این دفاع نصب نشده است."); return
    p["installed_defense"][iid] = installed - 1
    if p["installed_defense"][iid] <= 0: p["installed_defense"].pop(iid,None)
    # حذف از پایگاه، آیتم را دوباره به انبار برمی‌گرداند.
    if game_can_add(p,iid,1): game_add(p,iid,1)
    else: await q.message.edit_text("📦 انبار پر است؛ دفاع از پایگاه حذف نشد."); p["installed_defense"][iid] = installed; return
    game_save(); await q.message.edit_text(f"✅ {it['name'] if it else 'دفاع'} از پایگاه برداشته شد.")

async def game_base_upgrade(p, update):
    q = update.callback_query; cur = int(p["base_level"])
    if cur >= 20: await q.message.edit_text("🏠 پایگاه به سطح ۲۰ رسیده است."); return
    nxt = cur + 1; cost = 900 * nxt; steel = max(2, nxt // 2)
    if p["money"] < cost or not game_has(p,"steel_ingot",steel): await q.message.edit_text(f"❌ برای سطح {nxt}: 💰 {cost:,} پول و {steel} شمش فولاد لازم است."); return
    p["money"] -= cost; game_remove(p,"steel_ingot",steel); p["base_level"] = nxt; game_save(); await q.message.edit_text(f"✅ پایگاه به سطح {nxt} رسید.")

async def game_targets(p):
    out=[]
    for t in GAME_PLAYERS.values():
        if int(t.get("id",0)) == int(p["id"]): continue
        game_sync(t)
        if not game_protected(t): out.append(t)
    return sorted(out, key=lambda x:(int(x.get("level",1)), str(x.get("name",""))))

async def game_personal_attack_menu(p, update):
    q=update.callback_query; uid=p["id"]
    if p["level"]<8: await q.message.edit_text("🔒 حمله شخصی از سطح ۸ باز می‌شود."); return
    if not p.get("equipped_weapon"): await q.message.edit_text("⚔️ برای حمله شخصی باید ابتدا یک سلاح را تجهیز کنی."); return
    if game_protected(p): await q.message.edit_text("🛡 در دوره محافظت هستی."); return
    rows=[]
    for t in await game_targets(p): rows.append([InlineKeyboardButton(f"⚔️ {t['name']} | سطح {t['level']} | دفاع {game_personal_defense(t)}", callback_data=game_cb(uid,"aplayer",t['id']))])
    rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid,"menu"))])
    await q.message.edit_text("⚔️ حمله شخصی\n\nهدف را انتخاب کن:", reply_markup=InlineKeyboardMarkup(rows))

async def game_personal_attack_run(p, update, target_id):
    q=update.callback_query
    if p["level"]<8 or not p.get("equipped_weapon"): await q.message.edit_text("🔒 شرایط حمله شخصی کامل نیست."); return
    if game_protected(p) or p["energy"]<20: await q.message.edit_text("🛡 محافظت فعال است یا ⚡ انرژی کافی نداری."); return
    target=GAME_PLAYERS.get(str(target_id))
    if not target or int(target.get("id",0))==int(p["id"]): await q.message.edit_text("❌ هدف معتبر نیست."); return
    game_sync(target)
    if game_protected(target): await q.message.edit_text("🛡 این بازیکن در دوره محافظت است."); return
    p["energy"]-=20
    attack=game_personal_attack_power(p)+random.randint(0,15)
    defense=game_personal_defense(target)+random.randint(0,12)
    if attack>=defense:
        target["health"]=0; target["protected_until"]=time.time()+1800
        p["wins"]=int(p.get("wins",0))+1; target["losses"]=int(target.get("losses",0))+1
        p["daily_quests"]["personal_attack"]=1; reward=200+int(target.get("level",1))*50; p["money"]+=reward; game_xp(p,45)
        result=f"✅ حمله شخصی موفق بود.\n🛡 هدف تا ۳۰ دقیقه در محافظت است.\n💰 +{reward:,} پول\n⭐ +45 تجربه"
        try: await update.callback_query.get_bot().send_message(target["id"], f"🛡 دورهٔ محافظت ۳۰ دقیقه‌ای برای حساب شما فعال شد.")
        except Exception: pass
    else:
        p["losses"]=int(p.get("losses",0))+1
        p["health"]=max(0,int(p["health"])-20)
        if p["health"]==0: p["protected_until"]=time.time()+1800
        result="❌ حمله موفق نشد و مقداری از سلامت کم شد."
    game_log("personal_attack",p["id"],str(target_id)); game_save(); await q.message.edit_text(result)

async def game_base_attack_menu(p, update):
    q=update.callback_query; uid=p["id"]
    if p["level"]<20 or p["base_level"]<3: await q.message.edit_text("🔒 حمله پایگاه از سطح ۲۰ و پایگاه سطح ۳ فعال می‌شود."); return
    rows=[]
    for t in await game_targets(p):
        if int(t.get("base_level",1))>=2: rows.append([InlineKeyboardButton(f"🚀 {t['name']} | پایگاه {t['base_level']} | دفاع {game_base_defense(t)}", callback_data=game_cb(uid,"abase",t['id']))])
    rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid,"menu"))])
    await q.message.edit_text("🚀 حمله پایگاه\n\nبرای هر حمله ۱ پهپاد تهاجمی/فازی و ۱ موشک تاکتیکی/سنگین مصرف می‌شود.", reply_markup=InlineKeyboardMarkup(rows))

async def game_base_attack_run(p, update, target_id):
    q=update.callback_query
    if p["level"]<20 or p["base_level"]<3: await q.message.edit_text("🔒 شرایط حمله پایگاه کامل نیست."); return
    target=GAME_PLAYERS.get(str(target_id))
    if not target or int(target.get("id",0))==int(p["id"]): await q.message.edit_text("❌ هدف معتبر نیست."); return
    game_sync(target)
    if game_protected(p) or game_protected(target): await q.message.edit_text("🛡 حمله در دوره محافظت مجاز نیست."); return
    drone="phase_drone" if game_has(p,"phase_drone") else "assault_drone" if game_has(p,"assault_drone") else None
    missile="heavy_missile" if game_has(p,"heavy_missile") else "tactical_missile" if game_has(p,"tactical_missile") else None
    if not drone or not missile: await q.message.edit_text("❌ یک پهپاد تهاجمی/فازی و یک موشک لازم است."); return
    game_remove(p,drone,1); game_remove(p,missile,1)
    attack=game_base_attack_power(p)+int(game_item(drone).get("stats",{}).get("base_attack",0))+int(game_item(missile).get("stats",{}).get("missile_power",0))+random.randint(0,20)
    defense=game_base_defense(target)+random.randint(0,20)
    if attack>=defense:
        target["base_level"]=max(1,int(target["base_level"])-1); p["base_wins"]=int(p.get("base_wins",0))+1; target["base_losses"]=int(target.get("base_losses",0))+1; p["daily_quests"]["base_attack"]=1; game_xp(p,70)
        result=f"✅ حمله پایگاه موفق بود.\n🏠 سطح پایگاه هدف: {target['base_level']}"
    else:
        p["base_losses"]=int(p.get("base_losses",0))+1; result="❌ دفاع پایگاه حمله را متوقف کرد؛ تجهیزات حمله مصرف شدند."
    game_log("base_attack",p["id"],str(target_id)); game_save(); await q.message.edit_text(result)

async def game_market(p, update):
    q=update.callback_query; uid=p["id"]; active=[x for x in GAME_MARKET if not x.get("sold")]
    rows=[]
    for m in active[:30]:
        it=game_item(m.get("item_id"))
        if it: rows.append([InlineKeyboardButton(f"🛒 {it['name']} ×{m['qty']} | {int(m['price']):,}", callback_data=game_cb(uid,"mbuy",m['id']))])
    rows.append([InlineKeyboardButton("💰 فروش آیتم", callback_data=game_cb(uid,"msell"))]); rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid,"menu"))])
    await q.message.edit_text("🛒 بازار\n\nخرید و فروش مستقیم بین بازیکنان.", reply_markup=InlineKeyboardMarkup(rows))

async def game_market_sell_menu(p, update):
    q=update.callback_query; uid=p["id"]; rows=[]
    for iid, qty in p["inventory"].items():
        it=game_item(iid)
        if it and qty>0 and it.get("tradable"):
            rows.append([InlineKeyboardButton(f"💰 {it['name']} ×1 | {it['sell_price']:,}", callback_data=game_cb(uid,"mlist",iid))])
    rows.append([InlineKeyboardButton("⬅️ بازار", callback_data=game_cb(uid,"market"))])
    await q.message.edit_text("آیتمی را برای فروش با قیمت پایه انتخاب کن:", reply_markup=InlineKeyboardMarkup(rows))

async def game_market_list(p, update, iid):
    q=update.callback_query; it=game_item(iid)
    if not it or not game_has(p,iid,1): await q.message.edit_text("❌ آیتم موجود نیست."); return
    price=max(1,int(it.get("sell_price",1))); game_remove(p,iid,1)
    listing_id=f"m_{p['id']}_{int(time.time()*1000)}"
    GAME_MARKET.append({"id":listing_id,"seller_id":p["id"],"item_id":iid,"qty":1,"price":price,"sold":False,"created":now()})
    game_save(); await q.message.edit_text(f"✅ {it['name']} در بازار با قیمت {price:,} ثبت شد.")

async def game_market_buy(p, update, listing_id):
    q=update.callback_query; m=next((x for x in GAME_MARKET if x.get("id")==listing_id and not x.get("sold")),None)
    if not m: await q.message.edit_text("❌ این آگهی دیگر فعال نیست."); return
    if int(m["seller_id"])==int(p["id"]): await q.message.edit_text("❌ نمی‌توانی آگهی خودت را بخری."); return
    if p["money"]<int(m["price"]): await q.message.edit_text("💰 پول کافی نیست."); return
    if not game_can_add(p,m["item_id"],m["qty"]): await q.message.edit_text("📦 ظرفیت انبار کافی نیست."); return
    seller=GAME_PLAYERS.get(str(m["seller_id"]))
    if not seller: await q.message.edit_text("❌ فروشنده پیدا نشد."); return
    p["money"]-=int(m["price"]); seller["money"]=int(seller.get("money",0))+int(m["price"]); game_add(p,m["item_id"],m["qty"]); m["sold"]=True
    game_log("market_buy",p["id"],listing_id); game_save(); it=game_item(m["item_id"]); await q.message.edit_text(f"✅ خرید انجام شد: {it['name']} ×{m['qty']}")

async def game_quests(p, update):
    q=update.callback_query; d=p["daily_quests"]; done=all(int(d.get(k,0))>=v for k,v in (("extract",3),("explore",2),("personal_attack",1),("base_attack",1)))
    text=("📜 مأموریت‌های روزانه\n\n"
          f"⛏ استخراج: {d.get('extract',0)}/3\n🗺 کاوش: {d.get('explore',0)}/2\n⚔️ حمله شخصی: {d.get('personal_attack',0)}/1\n🚀 حمله پایگاه: {d.get('base_attack',0)}/1")
    rows=[]
    if done and not d.get("reward_claimed"): rows.append([InlineKeyboardButton("🎁 دریافت جایزه", callback_data=game_cb(p['id'],"qreward"))])
    rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(p['id'],"menu"))])
    await q.message.edit_text(text+ ("\n\n✅ همه کامل شده‌اند." if done else "\n\nادامه بده تا همه کامل شوند."), reply_markup=InlineKeyboardMarkup(rows))

async def game_quest_reward(p, update):
    q=update.callback_query; d=p["daily_quests"]
    if not all(int(d.get(k,0))>=v for k,v in (("extract",3),("explore",2),("personal_attack",1),("base_attack",1))): await q.message.edit_text("❌ هنوز همهٔ مأموریت‌ها کامل نشده‌اند."); return
    if d.get("reward_claimed"): await q.message.edit_text("✅ جایزهٔ امروز قبلاً دریافت شده است."); return
    p["money"]+=2500; game_xp(p,150); d["reward_claimed"]=True; game_save(); await q.message.edit_text("🎁 جایزه دریافت شد: 💰 +2,500 و ⭐ +150 تجربه")

async def game_daily(p, update):
    q=update.callback_query
    if p.get("daily_claimed"): await q.message.edit_text("✅ پاداش امروز قبلاً دریافت شده است."); return
    amount=500+int(p["level"])*50; p["money"]+=amount; game_xp(p,50); p["daily_claimed"]=True; game_save(); await q.message.edit_text(f"🎁 پاداش روزانه دریافت شد.\n💰 +{amount:,}\n⭐ +50 تجربه")

async def game_alliance(p, update):
    q=update.callback_query; uid=p["id"]; aid=p.get("alliance_id"); rows=[]
    if aid and str(aid) in GAME_ALLIANCES:
        a=GAME_ALLIANCES[str(aid)]; rows.append([InlineKeyboardButton("🚪 خروج از اتحاد", callback_data=game_cb(uid,"aleave"))]); text=f"🤝 اتحاد: {a['name']}\n\n👥 اعضا: {len(a.get('members',[]))}/20"
    else:
        rows.append([InlineKeyboardButton("➕ ساخت اتحاد", callback_data=game_cb(uid,"acreate"))])
        for aid2,a in list(GAME_ALLIANCES.items())[:20]:
            if len(a.get("members",[]))<20: rows.append([InlineKeyboardButton(f"🤝 {a['name']} | {len(a.get('members',[]))}/20", callback_data=game_cb(uid,"ajoin",aid2))])
        text="🤝 اتحادها\n\nیک اتحاد بساز یا به اتحاد موجود بپیوند."
    rows.append([InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid,"menu"))])
    await q.message.edit_text(text, reply_markup=InlineKeyboardMarkup(rows))

async def game_alliance_leave(p, update):
    q=update.callback_query; aid=str(p.get("alliance_id")) if p.get("alliance_id") else None
    if not aid or aid not in GAME_ALLIANCES: await q.message.edit_text("ℹ️ عضو اتحادی نیستی."); return
    a=GAME_ALLIANCES[aid]
    if int(a["owner_id"])==int(p["id"]):
        for mid in a.get("members",[]):
            x=GAME_PLAYERS.get(str(mid))
            if x: x["alliance_id"]=None
        GAME_ALLIANCES.pop(aid,None)
    else:
        a["members"]=[m for m in a.get("members",[]) if int(m)!=int(p["id"]) ]
        p["alliance_id"]=None
    game_save(); await q.message.edit_text("✅ وضعیت اتحاد به‌روزرسانی شد.")

async def game_alliance_join(p, update, aid):
    q=update.callback_query
    if p.get("alliance_id"): await q.message.edit_text("❌ ابتدا از اتحاد فعلی خارج شو."); return
    a=GAME_ALLIANCES.get(str(aid))
    if not a or len(a.get("members",[]))>=20: await q.message.edit_text("❌ اتحاد پیدا نشد یا ظرفیت آن پر است."); return
    a.setdefault("members",[]).append(p["id"]); p["alliance_id"]=str(aid); game_save(); await q.message.edit_text(f"✅ به اتحاد «{a['name']}» پیوستی.")

def game_admin_keyboard(page=1):
    return game_admin_markup(page)

# پنل مدیریت بازی — دکمه‌های واقعی و متصل به callback هستند.
def game_admin_markup(page=1):
    if page == 1:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 فهرست آیتم‌ها", callback_data="ga:list:1")],
            [InlineKeyboardButton("🖼 مدیریت عکس آیتم‌ها", callback_data="ga:images:1")],
            [InlineKeyboardButton("🗑 حذف/غیرفعال‌سازی آیتم", callback_data="ga:delete:1")],
            [InlineKeyboardButton("✏️ ویرایش قیمت آیتم", callback_data="ga:edit:1")],
            [InlineKeyboardButton("➕ افزودن آیتم", callback_data="ga:add")],
            [InlineKeyboardButton("📊 آمار بازی", callback_data="ga:stats")],
            [InlineKeyboardButton("➡️ صفحه ۲", callback_data="ga:page:2")],
        ])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 ساخت دوبارهٔ ۱۲۰ دستور ثابت", callback_data="ga:recipes")],
        [InlineKeyboardButton("💾 بکاپ اطلاعات بازی", callback_data="ga:backup")],
        [InlineKeyboardButton("🗂 ذخیره‌سازی", callback_data="ga:storage")],
        [InlineKeyboardButton("⬅️ صفحه ۱", callback_data="ga:page:1")],
    ])

async def game_admin_start(update, context):
    if not update.effective_user or not is_owner(update.effective_user.id) or not game_private(update):
        if update.effective_message: await update.effective_message.reply_text("❌ فقط مالک و فقط در خصوصی قابل استفاده است.")
        return
    await update.effective_message.reply_text("🎮 مدیریت بازی\n\nهمهٔ آیتم‌ها، عکس‌ها، قیمت‌ها و اطلاعات بازی از اینجا مدیریت می‌شوند.", reply_markup=game_admin_markup(1))

async def _game_admin_item_page(update, page, mode="list"):
    q=update.callback_query; page=max(1,int(page)); active=[x for x in GAME_ITEMS if x.get("active",True)]; chunk=active[(page-1)*12:page*12]; rows=[]
    for it in chunk:
        action={"images":"gsetimg", "delete":"gdel", "edit":"gedit"}.get(mode,"gnoop")
        rows.append([InlineKeyboardButton(it["name"], callback_data=f"ga:{action}:{it['id']}")])
    nav=[]
    if page>1: nav.append(InlineKeyboardButton("⬅️", callback_data=f"ga:{mode}:{page-1}"))
    if page*12<len(active): nav.append(InlineKeyboardButton("➡️", callback_data=f"ga:{mode}:{page+1}"))
    if nav: rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ پنل مدیریت بازی", callback_data="ga:home")])
    await q.message.edit_text(f"📦 فهرست آیتم‌ها — صفحه {page}", reply_markup=InlineKeyboardMarkup(rows))

async def game_admin_callback(update, context):
    q=update.callback_query
    if not q: return
    if not is_owner(q.from_user.id) or not q.message or q.message.chat.type != ChatType.PRIVATE:
        await q.answer("❌ دسترسی ندارید.", show_alert=True); return
    await q.answer()
    parts=q.data.split(":"); action=parts[1] if len(parts)>1 else ""
    if action=="home": await q.message.edit_text("🎮 مدیریت بازی", reply_markup=game_admin_markup(1)); return
    if action=="page": await q.message.edit_text(f"🎮 مدیریت بازی — صفحه {parts[2]}", reply_markup=game_admin_markup(int(parts[2]))); return
    if action in ("list","images","delete","edit"):
        await _game_admin_item_page(update, int(parts[2]) if len(parts)>2 else 1, action); return
    if action=="gsetimg":
        iid=parts[2]; it=game_item(iid)
        if not it: await q.message.edit_text("❌ آیتم پیدا نشد."); return
        context.user_data["game_img_item"]=iid; context.user_data["game_img_photo"]=True
        await q.message.edit_text(f"🖼 عکس «{it['name']}» را به‌صورت Photo بفرست."); return
    if action=="gdel":
        iid=parts[2]; it=game_item(iid)
        if it: it["active"]=False; game_save(); await q.message.edit_text(f"🗑 «{it['name']}» غیرفعال شد.")
        return
    if action=="gedit":
        iid=parts[2]; it=game_item(iid)
        if not it: return
        context.user_data["game_edit_item"]=iid; context.user_data["state"]="game_edit_price"
        await q.message.edit_text(f"✏️ قیمت جدید «{it['name']}» را فقط به‌صورت عدد بفرست.\nقیمت فعلی: {it['base_price']:,}"); return
    if action=="add":
        context.user_data["state"]="game_add_name"
        await q.message.edit_text("➕ نام آیتم جدید را بفرست:"); return
    if action=="stats":
        await q.message.edit_text(f"📊 آمار بازی\n\n👥 بازیکنان: {len(GAME_PLAYERS)}\n📦 آیتم‌های فعال: {sum(1 for x in GAME_ITEMS if x.get('active',True))}\n🧪 دستورهای ساخت: {len(GAME_RECIPES)}\n🛒 آگهی فعال بازار: {sum(1 for x in GAME_MARKET if not x.get('sold'))}\n🤝 اتحادها: {len(GAME_ALLIANCES)}"); return
    if action=="recipes":
        GAME_RECIPES.clear(); _seed_game_recipes(); GAME_STATE["schema"]=2; game_save(); await q.message.edit_text("✅ دقیقاً ۱۲۰ دستور ثابت بازسازی شد."); return
    if action=="storage":
        await q.message.edit_text(f"🗂 ذخیره‌سازی بازی\n\n📁 {GAME_DIR}") ; return
    if action=="backup":
        folder=BACKUP_DIR / f"game_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"; folder.mkdir(parents=True, exist_ok=True)
        for path in (GAME_PLAYERS_FILE,GAME_ITEMS_FILE,GAME_RECIPES_FILE,GAME_MARKET_FILE,GAME_ALLIANCES_FILE,GAME_STATE_FILE,GAME_LOG_FILE):
            if Path(path).exists(): shutil.copy2(path, folder / Path(path).name)
        await q.message.edit_text("✅ بکاپ بازی ساخته شد.") ; return
    if action=="gnoop": return

async def game_admin_photo(update, context):
    if not is_owner(update.effective_user.id): return False
    iid=context.user_data.get("game_img_item")
    if not iid or not update.message or not update.message.photo: return False
    file_id=update.message.photo[-1].file_id; it=game_item(iid)
    if not it: return False
    it["image_file_id"]=file_id; context.user_data.pop("game_img_item",None); context.user_data.pop("game_img_photo",None); game_save()
    await update.message.reply_text(f"✅ عکس «{it['name']}» ذخیره شد.")
    return True

async def game_admin_text(update, context):
    state=context.user_data.get("state"); text=(update.message.text or "").strip()
    if not is_owner(update.effective_user.id): return False
    if state=="game_edit_price":
        try: price=int(text)
        except ValueError: await update.message.reply_text("❌ قیمت باید عدد باشد."); return True
        iid=context.user_data.get("game_edit_item"); it=game_item(iid)
        if not it or price<1: await update.message.reply_text("❌ اطلاعات نامعتبر است."); return True
        it["base_price"]=price; it["sell_price"]=max(1,int(price*0.62)); game_save(); context.user_data.clear(); await update.message.reply_text(f"✅ قیمت «{it['name']}» تغییر کرد."); return True
    if state=="game_add_name":
        name=text[:50]
        if not name: await update.message.reply_text("❌ نام نامعتبر است."); return True
        context.user_data["game_new_name"]=name; context.user_data["state"]="game_add_price"; await update.message.reply_text("💰 قیمت پایه را بفرست:"); return True
    if state=="game_add_price":
        try: price=int(text)
        except ValueError: await update.message.reply_text("❌ قیمت باید عدد باشد."); return True
        if price<1: await update.message.reply_text("❌ قیمت باید مثبت باشد."); return True
        name=context.user_data.get("game_new_name","آیتم جدید"); iid=f"custom_{int(time.time()*1000)}"
        _game_add_item(_game_crafted_item(iid,name,"آیتم سفارشی","common",price,2,1,{})); game_save(); context.user_data.clear(); await update.message.reply_text(f"✅ آیتم «{name}» اضافه شد."); return True
    return False

async def game_callback(update, context):
    q=update.callback_query
    if not q: return
    parts=(q.data or "").split(":")
    if len(parts) < 3 or parts[0] != "ng":
        return
    try: owner_id=int(parts[1])
    except ValueError:
        await q.answer("❌ این پنل معتبر نیست.", show_alert=True); return
    if q.from_user.id != owner_id:
        await q.answer("❌ این دکمه برای شما نیست.", show_alert=True); return
    if not q.message or q.message.chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await q.answer("❌ بازی فقط داخل گروه قابل استفاده است.", show_alert=True); return
    await q.answer()
    parts=q.data.split(":"); uid=int(parts[1]); action=parts[2]; p=game_player(q.from_user)
    if action in PANEL_LEVELS and not game_panel_unlocked(p, action):
        await q.message.edit_text(game_locked_text(action), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ منو", callback_data=game_cb(uid, "menu"))]]))
        return
    try:
        if action in ("menu","profile"): await q.message.edit_text(game_profile_text(p), reply_markup=game_main_keyboard(uid)); return
        if action=="inventory": await game_inventory_private(p,update,int(parts[3]) if len(parts)>3 else 1); return
        if action=="item": await game_item_detail(p,update,parts[3]); return
        if action=="help": await q.message.edit_text(GAME_HELP,reply_markup=game_main_keyboard(uid)); return
        if action=="close": await q.message.edit_reply_markup(reply_markup=None); return
        if action=="explore": await game_explore_menu(p,update); return
        if action=="sections": await game_sections(p,update,int(parts[3])); return
        if action=="locked": await q.message.edit_text("🔒 این بخش هنوز باز نشده است."); return
        if action=="section": await game_section_preview(p,update,int(parts[3]),int(parts[4])); return
        if action=="run_explore": await game_run_explore(p,update,int(parts[3]),int(parts[4])); return
        if action in ("lab","workshop","factory"): await game_recipes(p,update,action,int(parts[3]) if len(parts)>3 else 1); return
        if action=="craft": await game_craft(p,update,parts[3]); return
        if action=="research":
            nxt=int(p["research_level"])+1
            rows=[] if nxt>10 else [[InlineKeyboardButton(f"⬆️ ارتقا به {nxt}",callback_data=game_cb(uid,"rup"))]]
            rows.append([InlineKeyboardButton("⬅️ منو",callback_data=game_cb(uid,"menu"))])
            await q.message.edit_text(f"🔬 تحقیق فعلی: {p['research_level']}/10",reply_markup=InlineKeyboardMarkup(rows)); return
        if action=="rup": await game_research(p,update); return
        if action=="equipment": await game_equipment(p,update); return
        if action=="equipw": await game_equip(p,update,"weapon",parts[3]); return
        if action=="equipa": await game_equip(p,update,"armor",parts[3]); return
        if action=="guard": await game_guard_upgrade(p,update); return
        if action=="pickaxe": await game_pickaxe_upgrade(p,update); return
        if action=="base": await game_base(p,update); return
        if action=="binstmenu": await game_base_defense_menu(p,update,False); return
        if action=="bremmenu": await game_base_defense_menu(p,update,True); return
        if action=="binst": await game_base_install(p,update,parts[3]); return
        if action=="brem": await game_base_remove(p,update,parts[3]); return
        if action=="bup": await game_base_upgrade(p,update); return
        if action=="personal_attack": await game_personal_attack_menu(p,update); return
        if action=="aplayer": await game_personal_attack_run(p,update,int(parts[3])); return
        if action=="base_attack": await game_base_attack_menu(p,update); return
        if action=="abase": await game_base_attack_run(p,update,int(parts[3])); return
        if action=="market": await game_market(p,update); return
        if action=="msell": await game_market_sell_menu(p,update); return
        if action=="mlist": await game_market_list(p,update,parts[3]); return
        if action=="mbuy": await game_market_buy(p,update,parts[3]); return
        if action=="quests": await game_quests(p,update); return
        if action=="qreward": await game_quest_reward(p,update); return
        if action=="daily": await game_daily(p,update); return
        if action=="alliance": await game_alliance(p,update); return
        if action=="acreate":
            context.user_data["state"]="game_alliance_create"; await q.message.edit_text("✍️ نام اتحاد را بفرست:"); return
        if action=="ajoin": await game_alliance_join(p,update,parts[3]); return
        if action=="aleave": await game_alliance_leave(p,update); return
        if action=="noop": return
        await q.message.edit_text("❌ این گزینه شناخته نشد.")
    except (ValueError, IndexError) as exc:
        await q.message.edit_text("❌ اطلاعات دکمه نامعتبر است.")
    except Exception as exc:
        game_log("callback_error", q.from_user.id, repr(exc)); game_save(); await q.message.edit_text("❌ اجرای این گزینه با خطا روبه‌رو شد. گزینه را دوباره باز کن.")

# ربات در تمام گروه‌ها قابل استفاده است؛ این تابع هیچ GROUP_ID ثابتی ندارد.
async def group_router(update, context):
    message=update.effective_message; user=update.effective_user
    if not message or not user or not game_group(update): return
    register_user(user); raw=(message.text or "").strip(); norm=normalize(raw)
    if norm in ("بازی","گیم","game","/game"):
        await game_start(update,context); return
    if norm in ("انبار","inventory","inv","/inventory","/inv"):
        await game_inventory_command(update,context); return
    if norm in ("راهنما","راهنمای بازی","gamehelp","/gamehelp"):
        await game_help_command(update,context); return
    if norm in ("استخراج","استخراج کردن"):
        await game_extract(update,user); return
    if norm in ("کاوش","explore","پنل خصوصی","پنل شخصی","پنل بازی خصوصی"):
        await game_start(update,context); return
    if norm in ("منوی ربات","منو","ربات","/menu","/bot","/nekoroom","راهنمای ربات"):
        await group_general_menu(update); return
    category={"انیمه":"anime","anime":"anime","فیلم":"movie","movie":"movie","موسیقی":"music","music":"music","مانگا":"manga","manga":"manga"}.get(norm)
    if category:
        if await check_membership(context.bot,user.id): await show_category(update,category)
        else: await membership_message(update)
        return
    if norm in ("تازه ها","تازه‌ها","جدیدها","new","/new"): await show_new(update); return
    if norm in ("محبوب ها","محبوب‌ها","محبوب","popular","/popular"): await show_popular(update); return
    if norm in ("تصادفی","پیشنهاد تصادفی","random","/random"): await random_content(update); return
    if norm in ("علاقه مندی ها","علاقه‌مندی‌ها","علاقه مندی","favorites","/favorites"): await show_favorites(update); return
    if norm in ("تاریخچه","history","/history"): await show_history(update); return
    if norm.startswith("/search"):
        query=raw[len("/search"):].strip()
        if not query: await message.reply_text("🔎 نام محتوا را بعد از /search بنویس."); return
        results=[x for x in contents if normalize(query) in normalize(x.get("name",""))]
        if not results: await message.reply_text("❌ چیزی پیدا نشد."); return
        rows=[[InlineKeyboardButton(x.get("name","-"),callback_data=f"content:{x['id']}")] for x in results[:30]]
        await message.reply_text(f"🔎 {len(results)} نتیجه:",reply_markup=InlineKeyboardMarkup(rows)); return
    if norm in ("جستجو","/search"):
        context.user_data["group_search"]=True; context.user_data["group_search_chat_id"]=update.effective_chat.id; await message.reply_text("🔎 نام محتوا را در همین گروه بفرست:"); return
    if context.user_data.get("group_search") and context.user_data.get("group_search_chat_id")==update.effective_chat.id:
        context.user_data.pop("group_search",None); context.user_data.pop("group_search_chat_id",None)
        results=[x for x in contents if normalize(raw) in normalize(x.get("name",""))]
        if not results: await message.reply_text("❌ چیزی پیدا نشد."); return
        rows=[[InlineKeyboardButton(x.get("name","-"),callback_data=f"content:{x['id']}")] for x in results[:30]]; await message.reply_text(f"🔎 {len(results)} نتیجه:",reply_markup=InlineKeyboardMarkup(rows))

async def group_general_menu(update):
    await update.effective_message.reply_text(
        "🤖 منوی Neko Room در گروه\n\n"
        "🎮 بازی: بازی یا /game\n🎒 انبار: انبار یا /inventory\n⛏ استخراج: استخراج\n🗺 کاوش: کاوش\n🔐 پنل خصوصی: پنل خصوصی\n❓ راهنما: راهنما یا /gamehelp\n\n"
        "🎬 انیمه | 🎥 فیلم | 🎵 موسیقی | 📚 مانگا\n🆕 تازه‌ها | 🔥 محبوب‌ها | 🎲 تصادفی | ⭐ علاقه‌مندی‌ها | 🕘 تاریخچه\n🔎 جستجو: /search نام محتوا"
    )

async def game_text_shortcuts(update,context):
    await group_router(update,context)

async def game_admin_command_alias(update, context):
    await game_admin_start(update,context)

async def file_router(update, context):
    if not update.message or not update.effective_user: return
    if context.user_data.get("game_img_photo") and await game_admin_photo(update,context): return
    if context.user_data.get("state") in ("add_files",):
        await receive_file(update,context)

async def callback_router(update, context):
    q=update.callback_query
    if not q: return
    data=q.data or ""
    if data.startswith("ng:"): await game_callback(update,context); return
    if data.startswith("ga:"): await game_admin_callback(update,context); return
    if data=="check_membership":
        if await check_membership(context.bot,q.from_user.id): await q.message.reply_text("✅ عضویت تأیید شد.",reply_markup=main_keyboard(q.from_user.id))
        else: await q.answer("❌ هنوز عضو کانال نیستی.",show_alert=True)
        return
    if data=="back_main": await q.message.reply_text("🏠 منوی اصلی",reply_markup=main_keyboard(q.from_user.id)); return
    if data.startswith("approve:"): await approve_request(update,context); return
    if data.startswith("reject:"): await reject_request(update,context); return
    if data=="owner_requests": await owner_requests(update,context); return
    if data=="contact_owner": await contact_owner(update,context); return
    if data=="owner_contact_admins": await owner_contact_admins(update,context); return
    if data.startswith("contact_admin:"): await select_admin(update,context); return
    if data.startswith("content:"): await content_callback(update,context); return
    if data.startswith("season:"): await season_callback(update,context); return
    if data.startswith("episode:"): await episode_callback(update,context); return
    if data.startswith("file:"): await file_callback(update,context); return
    if data.startswith("fav:"): await favorite_callback(update,context); return
    if data.startswith("add:"): await add_callback(update,context); return
    if data=="my_contents": await my_contents(update,context); return
    if data=="my_stats": await admin_stats(update,context); return
    if data.startswith("manage:"): await manage_content(update,context); return
    if data.startswith("delete:"): await delete_content(update,context); return
    if data=="game_admin": await game_admin_start(update,context); return
    if data.startswith("owner_") or data=="owner_panel":
        if data=="owner_panel": await q.message.reply_text("👑 پنل مالک",reply_markup=owner_keyboard())
        else: await owner_callback(update,context)
        return

async def group_command_handler(update, context):
    await group_router(update, context)

async def get_id(update, context):
    if update.effective_message and update.effective_user:
        await update.effective_message.reply_text(f"🆔 آیدی عددی شما:\n\n{update.effective_user.id}")

async def error_handler(update, context):
    print("❌ خطای ربات:", repr(context.error))

async def owner_add_points(update, context):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ مقدار را درست وارد کنید.\nمثال: /addpoints 500")
        return
    if amount < 0:
        await update.message.reply_text("❌ مقدار نمی‌تواند منفی باشد.")
        return
    value = get_points(OWNER_ID) + amount
    set_points(OWNER_ID, value)
    await update.message.reply_text(f"⭐ +{amount} امتیاز اضافه شد.\nامتیاز فعلی: {value}")


async def owner_remove_points(update, context):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ مقدار را درست وارد کنید.\nمثال: /removepoints 200")
        return
    if amount < 0:
        await update.message.reply_text("❌ مقدار نمی‌تواند منفی باشد.")
        return
    value = max(0, get_points(OWNER_ID) - amount)
    set_points(OWNER_ID, value)
    await update.message.reply_text(f"⭐ -{amount} امتیاز کم شد.\nامتیاز فعلی: {value}")


def main():
    app=Application.builder().token(TOKEN).build()
    private=filters.ChatType.PRIVATE
    group=filters.ChatType.GROUP | filters.ChatType.SUPERGROUP

    # دستورات خصوصی
    app.add_handler(CommandHandler("start", start, filters=private))
    app.add_handler(CommandHandler("id", get_id))
    app.add_handler(CommandHandler("game", game_start))
    app.add_handler(CommandHandler("game_admin", game_admin_start, filters=private))
    app.add_handler(CommandHandler("inventory", game_inventory_command))
    app.add_handler(CommandHandler("inv", game_inventory_command))
    app.add_handler(CommandHandler("gamehelp", game_help_command))
    app.add_handler(CommandHandler("addpoints", owner_add_points, filters=private))
    app.add_handler(CommandHandler("removepoints", owner_remove_points, filters=private))

    # دستورات عمومی در هر گروه؛ هیچ GROUP_ID ثابتی وجود ندارد.
    for cmd in ("menu","bot","nekoroom","anime","movie","music","manga","new","popular","random","favorites","history","search"):
        app.add_handler(CommandHandler(cmd, group_command_handler, filters=group))
    app.add_handler(CommandHandler("game", game_start, filters=group))
    app.add_handler(CommandHandler("inventory", game_inventory_command, filters=group))
    app.add_handler(CommandHandler("inv", game_inventory_command, filters=group))
    app.add_handler(CommandHandler("gamehelp", game_help_command, filters=group))

    # پیام‌های عادی گروه. در BotFather باید Privacy Mode خاموش باشد تا کلمات بدون / برسند.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & group, group_router))

    # callback واحد
    app.add_handler(CallbackQueryHandler(callback_router))

    # رسانه‌های خصوصی برای مدیریت محتوا/عکس آیتم
    media_filter=(filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.PHOTO) & private
    app.add_handler(MessageHandler(media_filter, file_router))

    # متن‌های خصوصی
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & private, text_router))
    app.add_error_handler(error_handler)

    game_save()
    print("="*56)
    print("        🤖 Neko Room BOT — آمادهٔ اجرا")
    print("="*56)
    print(f"👑 مالک: {OWNER_ID}")
    print(f"👮 تعداد ادمین‌ها: {len(admins)}")
    print("🎮 بازی: فعال در تمام گروه‌هایی که ربات داخل آن‌هاست")
    print(f"📦 آیتم‌های فعال: {sum(1 for x in GAME_ITEMS if x.get('active', True))}")
    print(f"🧪 دستورهای ساخت: {len(GAME_RECIPES)}")
    print("✅ همهٔ قابلیت‌های گروهی آماده‌اند.")
    print("="*56)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


# OWNER PANEL
# =========================================================

def owner_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📨 درخواست‌های ادمین‌ها",
                callback_data="owner_requests"
            )
        ],

        [
            InlineKeyboardButton(
                "📩 ارتباط با ادمین",
                callback_data="owner_contact_admins"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="owner_users"
            )
        ],

        [
            InlineKeyboardButton(
                "➕ افزودن ادمین",
                callback_data="owner_add_admin"
            ),

            InlineKeyboardButton(
                "➖ حذف ادمین",
                callback_data="owner_remove_admin"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 لیست ادمین‌ها",
                callback_data="owner_admins"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار کامل",
                callback_data="owner_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 ارسال همگانی",
                callback_data="owner_broadcast"
            )
        ],

        [
            InlineKeyboardButton(
                "📜 فعالیت‌ها",
                callback_data="owner_activity"
            )
        ],

        [
            InlineKeyboardButton(
                "💾 بکاپ",
                callback_data="owner_backup"
            )
        ],
        [
            InlineKeyboardButton(
                "🎮 مدیریت بازی",
                callback_data="game_admin"
            )
        ]

    ])


async def owner_panel(update):

    if not is_owner(
        update.effective_user.id
    ):
        return

    await update.message.reply_text(
        "👑 پنل مالک",
        reply_markup=owner_keyboard()
    )


# =========================================================
# OWNER CALLBACK
# =========================================================

async def owner_callback(
    update,
    context
):

    query = update.callback_query
    await query.answer()

    if not is_owner(
        query.from_user.id
    ):
        return

    action = query.data

    if action == "game_admin":
        await query.message.reply_text("🎮 مدیریت بازی", reply_markup=game_admin_keyboard(1))
        return

    if action.startswith("owner_deladmin:"):
        try:
            admin_id = int(action.split(":", 1)[1])
        except ValueError:
            await query.message.reply_text("❌ شناسه نامعتبر است.")
            return
        if admin_id not in admins:
            await query.message.reply_text("⚠️ این شخص ادمین نیست.")
            return
        admins.remove(admin_id)
        save_json(ADMINS_FILE, admins)
        log_activity(OWNER_ID, "remove_admin", str(admin_id))

        # از این لحظه is_admin برای این شخص False است؛ بنابراین
        # پنل مدیریت دیگر در منوی اصلی او ساخته نمی‌شود.
        await query.message.reply_text(
            f"✅ ادمین به طور کامل حذف شد.\n\n🆔 {admin_id}\n\n"
            "از این به بعد پنل مدیریت برای او نمایش داده نمی‌شود."
        )
        return

    # کاربران
    if action == "owner_users":

        text = (
            f"👥 تعداد کاربران: "
            f"{len(users)}\n\n"
        )

        for user in users[:50]:

            username = user.get(
                "username"
            )

            if username:
                username = (
                    f"@{username}"
                )
            else:
                username = "-"

            text += (
                f"👤 {user.get('first_name')}\n"
                f"🔹 {username}\n"
                f"🆔 {user.get('id')}\n"
                f"⬇️ {user.get('downloads', 0)}\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # لیست ادمین‌ها
    if action == "owner_admins":

        text = "👮 لیست ادمین‌ها:\n\n"
        keyboard = []

        for admin_id in admins:
            user = get_user(admin_id)
            name = user.get("first_name", "-") if user else "-"
            username = user.get("username") if user else None

            try:
                chat = await context.bot.get_chat(admin_id)
                name = chat.full_name or name or "-"
                username = chat.username or username
            except Exception:
                pass

            if username:
                text += f"👤 {name}\n🔹 @{username}\n🆔 {admin_id}\n\n"
                label = f"❌ حذف {name} | @{username}"
            else:
                text += f"👤 {name}\n🔹 -\n🆔 {admin_id}\n\n"
                label = f"❌ حذف {name}"

            keyboard.append([
                InlineKeyboardButton(label, callback_data=f"owner_deladmin:{admin_id}")
            ])

        await query.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
        return

    # افزودن ادمین
    if action == "owner_add_admin":

        context.user_data["state"] = (
            "add_admin"
        )

        await query.message.reply_text(
            "🆔 آیدی عددی ادمین جدید را بفرست:"
        )

        return

    # حذف ادمین — پنل انتخاب ادمین
    if action == "owner_remove_admin":
        admin_ids = [admin_id for admin_id in admins if admin_id != OWNER_ID]

        if not admin_ids:
            await query.message.reply_text("👮 ادمینی برای حذف وجود ندارد.")
            return

        keyboard = []
        for admin_id in admin_ids:
            user = get_user(admin_id)
            name = user.get("first_name", "-") if user else "-"
            username = user.get("username") if user else None

            try:
                chat = await context.bot.get_chat(admin_id)
                name = chat.full_name or name or "-"
                username = chat.username or username
            except Exception:
                pass

            label = f"❌ {name}"
            if username:
                label += f" | @{username}"
            label += f" | {admin_id}"

            keyboard.append([
                InlineKeyboardButton(
                    label,
                    callback_data=f"owner_deladmin:{admin_id}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("⬅️ برگشت", callback_data="owner_panel")
        ])

        await query.message.reply_text(
            "➖ حذف ادمین\n\nادمینی را که می‌خواهی کامل حذف شود انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # آمار
    if action == "owner_stats":

        downloads = sum(
            item.get("downloads", 0)
            for item in contents
        )

        await query.message.reply_text(
            "📊 آمار کامل\n\n"
            f"👥 کاربران: {len(users)}\n"
            f"👮 ادمین‌ها: {len(admins)}\n"
            f"📂 محتواها: {len(contents)}\n"
            f"⬇️ دانلودها: {downloads}\n"
            f"📜 فعالیت‌ها: {len(activity)}"
        )

        return

    # ارسال همگانی
    if action == "owner_broadcast":

        context.user_data["state"] = (
            "broadcast"
        )

        await query.message.reply_text(
            "📢 متن پیام همگانی را بفرست:"
        )

        return

    # فعالیت
    if action == "owner_activity":

        recent = activity[-30:]

        if not recent:

            await query.message.reply_text(
                "📜 فعالیتی ثبت نشده."
            )

            return

        text = "📜 آخرین فعالیت‌ها:\n\n"

        for item in reversed(
            recent
        ):

            text += (
                f"🕒 {item.get('time')}\n"
                f"🆔 {item.get('user_id')}\n"
                f"🔹 {item.get('action')}\n"
                f"{item.get('details')}\n\n"
            )

        await query.message.reply_text(
            text
        )

        return

    # بکاپ
    if action == "owner_backup":

        files = [
            USERS_FILE,
            ADMINS_FILE,
            CONTENT_FILE,
            REQUESTS_FILE,
            ACTIVITY_FILE
        ]

        for path in files:

            if os.path.exists(path):

                shutil.copy(
                    path,
                    os.path.join(
                        BACKUP_DIR,
                        os.path.basename(path)
                    )
                )

        await query.message.reply_text(
            "💾 بکاپ با موفقیت ساخته شد.\n\n"
            "📁 پوشه: backup"
        )

        return


# =========================================================
# OWNER TEXT
# =========================================================

async def receive_admin_id(
    update,
    context
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    try:

        admin_id = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ آیدی باید عددی باشد."
        )

        return

    if admin_id == OWNER_ID:

        await update.message.reply_text(
            "👑 این آیدی متعلق به مالک است."
        )

        context.user_data.clear()

        return

    if admin_id in admins:

        await update.message.reply_text(
            "⚠️ این شخص قبلاً ادمین است."
        )

        context.user_data.clear()

        return

    admins.append(
        admin_id
    )

    save_json(
        ADMINS_FILE,
        admins
    )

    log_activity(
        OWNER_ID,
        "add_admin",
        str(admin_id)
    )

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ ادمین اضافه شد.\n\n"
        f"🆔 {admin_id}"
    )


async def remove_admin_id(
    update,
    context
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    try:

        admin_id = int(
            update.message.text.strip()
        )

    except ValueError:

        await update.message.reply_text(
            "❌ آیدی باید عددی باشد."
        )

        return

    if admin_id not in admins:

        await update.message.reply_text(
            "⚠️ این آیدی ادمین نیست."
        )

        context.user_data.clear()

        return

    admins.remove(
        admin_id
    )

    save_json(
        ADMINS_FILE,
        admins
    )

    log_activity(
        OWNER_ID,
        "remove_admin",
        str(admin_id)
    )

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ ادمین حذف شد.\n\n"
        f"🆔 {admin_id}"
    )


# =========================================================
# BROADCAST
# =========================================================

async def broadcast(
    update,
    context
):

    if not is_owner(
        update.effective_user.id
    ):
        return

    text = update.message.text

    success = 0
    failed = 0

    for user in users:

        try:

            await context.bot.send_message(
                user["id"],
                "📢 پیام از طرف Neko Room:\n\n"
                + text
            )

            success += 1

        except Exception:

            failed += 1

    context.user_data.clear()

    await update.message.reply_text(
        "📢 ارسال همگانی تمام شد.\n\n"
        f"✅ موفق: {success}\n"
        f"❌ ناموفق: {failed}"
    )


# =========================================================

# OWNER SECRET POINT COMMANDS
# =========================================================

def get_points(user_id):
    user = get_user(user_id)
    if not user:
        return 0
    try:
        return int(user.get("points", 0))
    except (TypeError, ValueError):
        return 0


def set_points(user_id, value):
    user = get_user(user_id)
    if not user:
        users.append({
            "id": user_id,
            "username": None,
            "first_name": "کاربر",
            "last_seen": now(),
            "downloads": 0,
            "favorites": [],
            "history": [],
            "following": [],
            "points": max(0, int(value))
        })
    else:
        user["points"] = max(0, int(value))
    save_json(USERS_FILE, users)


# =========================================================


# =========================================================
# =========================================================
# مسیر متن خصوصی
# =========================================================

async def text_router(update, context):
    if not update.message or not update.message.text: return
    user=update.effective_user
    if not user: return
    register_user(user)
    text=update.message.text.strip()
    norm=normalize(text)
    state=context.user_data.get("state")

    if state and str(state).startswith("game_"):
        if await game_admin_text(update,context): return
        if state=="game_alliance_create":
            name=text[:32]
            p=game_player(user)
            if p.get("alliance_id"):
                context.user_data.clear(); await update.message.reply_text("❌ ابتدا از اتحاد فعلی خارج شو."); return
            if not name:
                await update.message.reply_text("❌ نام اتحاد نامعتبر است."); return
            aid=f"a_{user.id}_{int(time.time()*1000)}"
            GAME_ALLIANCES[aid]={"id":aid,"name":name,"owner_id":p["id"],"members":[p["id"]],"created":now()}
            p["alliance_id"]=aid; context.user_data.clear(); game_save(); await update.message.reply_text(f"✅ اتحاد «{name}» ساخته شد."); return

    if state=="contact_owner" or state=="contact_admin": await contact_text(update,context); return
    if state=="add_admin": await receive_admin_id(update,context); return
    if state=="remove_admin": await remove_admin_id(update,context); return
    if state=="broadcast": await broadcast(update,context); return
    if state=="search": await search_content(update,context); return
    if state=="add_name": await receive_name(update,context); return
    if state=="add_season": await receive_season(update,context); return
    if state=="add_files":
        if text=="✅ پایان": await finish_upload(update,context)
        return

    if norm in ("بازی","گیم","game","/game","🎮 بازی"):
        await game_start(update,context); return
    if norm in ("انبار","inventory","inv","/inventory","/inv"):
        await game_inventory_command(update,context); return
    if norm in ("راهنما","راهنمای بازی","gamehelp","/gamehelp"):
        await game_help_command(update,context); return
    if norm in ("پنل خصوصی","پنل شخصی"):
        p=game_player(user); await update.message.reply_text(game_profile_text(p),reply_markup=game_main_keyboard(user.id)); return

    if text=="🎬 انیمه":
        if await check_membership(context.bot,user.id): await show_category(update,"anime")
        else: await membership_message(update)
        return
    if text=="🎥 فیلم":
        if await check_membership(context.bot,user.id): await show_category(update,"movie")
        else: await membership_message(update)
        return
    if text=="🎵 موسیقی":
        if await check_membership(context.bot,user.id): await show_category(update,"music")
        else: await membership_message(update)
        return
    if text=="📚 مانگا":
        if await check_membership(context.bot,user.id): await show_category(update,"manga")
        else: await membership_message(update)
        return
    if text=="🔎 جستجو": await start_search(update,context); return
    if text=="🆕 تازه‌ها": await show_new(update); return
    if text=="🔥 محبوب‌ها": await show_popular(update); return
    if text=="🎲 پیشنهاد تصادفی": await random_content(update); return
    if text=="⭐ علاقه‌مندی‌ها": await show_favorites(update); return
    if text=="🕘 تاریخچه": await show_history(update); return
    if text=="⚙️ پنل مدیریت" and is_admin(user.id): await admin_panel(update); return
    if text=="👑 پنل مالک" and is_owner(user.id): await owner_panel(update); return

if __name__ == "__main__":
    main()
