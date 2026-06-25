import asyncio
import logging
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

OWNER_ID    = 8418787162         # ← ВСТАВЬТЕ ВАШ TELEGRAM ID

ADMINS_FILE = "admins.json"
STATS_FILE  = "stats.json"
STATUS_FILE = "bot_status.json"

WELCOME_STICKER = "CAACAgUAAxkBAzO9_GorAYlsF8_CBld2lHD6eAbFv2YTAAJdEQACr3tRVZEquUWHNk4oPAQ"
QR_IMAGE_PATH   = "qr.png"
CARD_NUMBER     = "0000 0000 0000 0000"   # ← ваша карта

# ── ID кастомных эмодзи для кнопок (Bot API 9.4+) ─────────────────────────
# Замените каждый ID на свой (получить у @getidsbot или @emoji_id_bot)
EMO_STARS   = "5954188131098956866"   # ⭐️ Звёзды
EMO_PREMIUM = "5260725503215543617"   # 💎 Премиум звезда
EMO_SELF    = "5368324170671202286"   # 👤 Себе
EMO_GIFT    = "5425109608328891010"   # 🎁 Подарок
EMO_BACK    = "5456187398977247949"   # ◀️ Назад
EMO_QR      = "5422814644093868925"   # 📷 QR-Code
EMO_CARD    = "5262495450648300372"   # 💳 По карте
EMO_HOME    = "5368324170671202286"   # 🏠 В начало
EMO_ADMIN   = "5368324170671202286"   # 🛠 Админ-панель
EMO_STATS   = "5368324170671202286"   # 📊 Статистика
EMO_ADDADM  = "5368324170671202286"   # ➕ Добавить админа
EMO_STOP    = "5368324170671202286"   # 🔴 Выключить
EMO_START   = "5368324170671202286"   # 🟢 Включить
EMO_PENCIL  = "5935938364086685805"   # ✏️ Выбрать количество
EMO_3MON    = "5368324170671202286"   # 🗓 3 месяца
EMO_6MON    = "5368324170671202286"   # 🗓 6 месяцев
EMO_12MON   = "5368324170671202286"   # 🗓 12 месяцев
EMO_SBP     = "5368324170671202286"   # 💸 СБП
EMO_CALENDAR= "5368324170671202286"   # 🗓 Длительность
EMO_MONEY   = "5368324170671202286"   # 💰 Стоимость

# ──────────────────────────── хранилище ───────────────────────────────────

def load_json(path, default):
    if os.path.exists(path):
        try:
            content = open(path, encoding="utf-8").read().strip()
            return json.loads(content) if content else default
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_admins() -> list:
    return load_json(ADMINS_FILE, [])

def save_admins(a: list):
    save_json(ADMINS_FILE, a)

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID or uid in get_admins()

def get_stats() -> dict:
    return load_json(STATS_FILE, {})

def save_stats(s: dict):
    save_json(STATS_FILE, s)

def is_active() -> bool:
    return load_json(STATUS_FILE, {"active": True}).get("active", True)

def set_active(val: bool):
    save_json(STATUS_FILE, {"active": val})

def add_purchase(buyer_id, buyer_uname, recipient, stars, amount, method):
    stats = get_stats()
    key = str(buyer_id)
    if key not in stats:
        stats[key] = {"username": buyer_uname or "None", "purchases": []}
    else:
        stats[key]["username"] = buyer_uname or "None"
    # Добавляем в конец — порядок от старых к новым
    stats[key]["purchases"].append({
        "recipient": recipient,
        "stars": stars,
        "amount_rub": round(amount, 2),
        "method": method,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_stats(stats)

# ──────────────────────────── состояния ───────────────────────────────────

class St(StatesGroup):
    waiting_recipient         = State()
    waiting_stars             = State()
    waiting_add_admin         = State()
    waiting_premium_recipient = State()

# ──────────────────────────── клавиатуры ──────────────────────────────────

def btn(text, cb, emo=None):
    """Создаёт кнопку с опциональным кастомным эмодзи."""
    if emo:
        return InlineKeyboardButton(text=text, callback_data=cb, icon_custom_emoji_id=emo)
    return InlineKeyboardButton(text=text, callback_data=cb)

def kb_main(uid: int):
    rows = [
        [btn("⭐️ Звёзды",          "stars",   EMO_STARS)],
        [btn("💎 Telegram Premium", "premium", EMO_PREMIUM)],
    ]
    if is_admin(uid):
        rows.append([btn("🛠 Админ-панель", "admin_panel", EMO_ADMIN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_stars_for():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("👤 Себе",    "stars_self", EMO_SELF),
         btn("🎁 Подарить","stars_gift", EMO_GIFT)],
        [btn("◀️ Назад",   "back_main",  EMO_BACK)],
    ])

def kb_no_username():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("◀️ Назад", "back_stars", EMO_BACK)],
    ])

def kb_amounts():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("50 ⭐️",  "amount_50",  EMO_STARS),
         btn("150 ⭐️", "amount_150", EMO_STARS),
         btn("250 ⭐️", "amount_250", EMO_STARS)],
        [btn("350 ⭐️", "amount_350", EMO_STARS),
         btn("500 ⭐️", "amount_500", EMO_STARS),
         btn("1000 ⭐️","amount_1000",EMO_STARS)],
        [btn("✏️ Выбрать количество звёзд", "amount_custom", EMO_PENCIL)],
        [btn("◀️ Назад", "back_stars", EMO_BACK)],
    ])

def kb_payment():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("💸 СБП — жду подтверждения от lava.ru", "stars_sbp", EMO_SBP)],
        [btn("◀️ Назад", "back_amounts", EMO_BACK)],
    ])

def kb_to_start():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("🏠 В начало", "back_main", EMO_HOME)],
    ])

def kb_admin(uid: int):
    rows = [
        [btn("📊 Статистика",      "admin_stats", EMO_STATS)],
        [btn("➕ Добавить админа", "admin_add",   EMO_ADDADM)],
    ]
    if uid == OWNER_ID:
        if is_active():
            rows.append([btn("🔴 Выключить бота", "admin_stop",  EMO_STOP)])
        else:
            rows.append([btn("🟢 Включить бота",  "admin_start", EMO_START)])
    rows.append([btn("◀️ Назад", "back_main", EMO_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_admin_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("◀️ Назад в панель", "admin_panel", EMO_BACK)],
    ])

def kb_stats_users(stats: dict):
    rows = []
    for uid, info in stats.items():
        uname = info.get("username", "None")
        count = len(info.get("purchases", []))
        label = f"@{uname} ({count} покупок)" if uname != "None" else f"ID:{uid} ({count} покупок)"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"stat_user_{uid}")])
    rows.append([btn("◀️ Назад в панель", "admin_panel", EMO_BACK)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_stat_user_back():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("◀️ К списку", "admin_stats", EMO_BACK)],
    ])

def kb_premium_for():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("👤 Себе",     "premium_self", EMO_SELF),
         btn("🎁 Подарить", "premium_gift", EMO_GIFT)],
        [btn("◀️ Назад",    "back_main",    EMO_BACK)],
    ])

def kb_premium_duration():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("🗓 3 месяца — 1249₽",   "prem_dur_3",  EMO_3MON)],
        [btn("🗓 6 месяцев — 1549₽",  "prem_dur_6",  EMO_6MON)],
        [btn("🗓 12 месяцев — 2799₽", "prem_dur_12", EMO_12MON)],
        [btn("◀️ Назад", "back_premium_for", EMO_BACK)],
    ])

def kb_premium_pay():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("💸 СБП - жду подтверждения lava.ru", "premium_sbp", EMO_SBP)],
        [btn("◀️ Назад", "back_premium_duration", EMO_BACK)],
    ])

# ──────────────────────────── helpers ─────────────────────────────────────

async def del_msg(bot: Bot, chat_id: int, msg_id):
    if msg_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

async def check_username_exists(username: str) -> bool:
    import urllib.request
    def _check():
        try:
            url = f"https://t.me/{username}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                return "tgme_page_title" in r.read().decode("utf-8", errors="ignore")
        except Exception:
            return False
    return await asyncio.get_event_loop().run_in_executor(None, _check)

def calc_price(stars: int) -> float:
    return stars * 1.525

MAINTENANCE_MSG = "🔧 Бот на тех. работах, как только он включится, мы вам сообщим"

# ──────────────────────────── /start ──────────────────────────────────────

async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    uid = message.from_user.id
    sd  = await state.get_data()
    await del_msg(bot, message.chat.id, sd.get("last_bot_msg"))
    await state.clear()

    if not is_active() and not is_admin(uid):
        await message.answer(MAINTENANCE_MSG)
        return

    try:
        await message.answer_sticker(WELCOME_STICKER)
    except Exception:
        pass

    sent = await message.answer(
        "✨ Добро пожаловать!\n\nВыберите раздел:",
        reply_markup=kb_main(uid),
        parse_mode="HTML"
    )
    await state.update_data(last_bot_msg=sent.message_id)

# ──────────────────────────── callback ────────────────────────────────────

async def handle_callback(call: CallbackQuery, state: FSMContext, bot: Bot):
    # call.answer() — ПЕРВЫМ делом, до любых долгих операций
    try:
        await call.answer()
    except Exception:
        pass

    uid  = call.from_user.id
    data = call.data
    chat = call.message.chat.id
    sd   = await state.get_data()
    last = sd.get("last_bot_msg")

    # Техработы
    if not is_active() and not is_admin(uid):
        try:
            await call.answer(MAINTENANCE_MSG, show_alert=True)
        except Exception:
            pass
        return

    async def replace(text: str, markup: InlineKeyboardMarkup):
        await del_msg(bot, chat, last)
        sent = await bot.send_message(chat, text, reply_markup=markup, parse_mode="HTML")
        await state.update_data(last_bot_msg=sent.message_id)

    # ── Главное меню ──────────────────────────────────────────────────────
    if data == "back_main":
        await state.set_state(None)
        await replace("✨ Выберите раздел:", kb_main(uid))

    elif data == "premium":
        await replace(
            "<tg-emoji emoji-id='" + EMO_PREMIUM + "'>💎</tg-emoji> <b>Telegram Premium</b>\n\nВыберите тип покупки:",
            kb_premium_for()
        )

    elif data == "back_premium_for":
        await state.set_state(None)
        await state.update_data(premium_recipient=None)
        await replace(
            "<tg-emoji emoji-id='" + EMO_PREMIUM + "'>💎</tg-emoji> <b>Telegram Premium</b>\n\nВыберите тип покупки:",
            kb_premium_for()
        )

    elif data == "premium_self":
        uname = call.from_user.username
        if not uname:
            await replace(
                "❗️У вас не установлен @username.\n\n"
                "‼️Вам нужно перейти в «Настройки» — «Мой аккаунт» — «Имя пользователя». "
                "Далее установите желаемый @username и повторите попытку.",
                kb_no_username()
            )
            return
        await state.update_data(premium_recipient=uname)
        await replace(
            f"<tg-emoji emoji-id='{EMO_PREMIUM}'>💎</tg-emoji> Premium подарок для @{uname}\n\n"
            f"<tg-emoji emoji-id='{EMO_CALENDAR}'>🗓</tg-emoji> Выберите длительность подписки:",
            kb_premium_duration()
        )

    elif data == "premium_gift":
        await del_msg(bot, chat, last)
        sent = await bot.send_message(
            chat,
            f"<tg-emoji emoji-id='{EMO_GIFT}'>🎁</tg-emoji> Введите @username получателя Premium:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("◀️ Назад", "back_premium_for", EMO_BACK)]
            ]),
            parse_mode="HTML"
        )
        await state.update_data(last_bot_msg=sent.message_id)
        await state.set_state(St.waiting_premium_recipient)

    elif data == "back_premium_duration":
        rec = (await state.get_data()).get("premium_recipient", "")
        await replace(
            f"<tg-emoji emoji-id='{EMO_PREMIUM}'>💎</tg-emoji> Premium подарок для @{rec}\n\n"
            f"<tg-emoji emoji-id='{EMO_CALENDAR}'>🗓</tg-emoji> Выберите длительность подписки:",
            kb_premium_duration()
        )

    elif data in ("prem_dur_3", "prem_dur_6", "prem_dur_12"):
        rec = sd.get("premium_recipient", "")
        dur_map = {
            "prem_dur_3":  ("3 месяца",  1249),
            "prem_dur_6":  ("6 месяцев", 1549),
            "prem_dur_12": ("1 год",     2799),
        }
        dur_label, price = dur_map[data]
        await state.update_data(premium_duration=dur_label, premium_price=price)
        await replace(
            f"<tg-emoji emoji-id='{EMO_PREMIUM}'>⭐️</tg-emoji> Telegram Премиум\n"
            f"<tg-emoji emoji-id='{EMO_GIFT}'>🎁</tg-emoji> Подарок для @{rec}\n"
            f"<tg-emoji emoji-id='{EMO_CALENDAR}'>🗓</tg-emoji> Длительность: {dur_label}\n"
            f"<tg-emoji emoji-id='{EMO_MONEY}'>💰</tg-emoji> Стоимость: {price} ₽\n\n"
            f"Выберите метод оплаты 👇",
            kb_premium_pay()
        )

    elif data == "premium_sbp":
        await call.answer("💸 СБП — раздел в разработке", show_alert=True)

    elif data == "stars":
        await replace("⭐️ <b>Telegram Звезды</b>\n\nВыберите тип покупки:", kb_stars_for())

    # ── Звёзды ────────────────────────────────────────────────────────────
    elif data == "back_stars":
        await state.set_state(None)
        await state.update_data(recipient=None)
        await replace("⭐️ <b>Telegram Звезды</b>\n\nВыберите тип покупки:", kb_stars_for())

    elif data == "stars_self":
        uname = call.from_user.username
        if not uname:
            await replace(
                "❗️У вас не установлен @username.\n\n"
                "‼️Вам нужно перейти в «Настройки» — «Мой аккаунт» — «Имя пользователя». "
                "Далее установите желаемый @username и повторите попытку.",
                kb_no_username()
            )
            return
        await state.update_data(recipient=uname)
        await replace(f"⭐️ <b>Звёзды для @{uname}</b>\n\nВыберите количество:", kb_amounts())

    elif data == "stars_gift":
        await del_msg(bot, chat, last)
        sent = await bot.send_message(
            chat, "Введите @username получателя:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("◀️ Назад", "back_stars", EMO_BACK)]
            ])
        )
        await state.update_data(last_bot_msg=sent.message_id)
        await state.set_state(St.waiting_recipient)

    # ── Количество ────────────────────────────────────────────────────────
    elif data == "back_amounts":
        rec = sd.get("recipient", "")
        await replace(f"⭐️ <b>Звёзды для @{rec}</b>\n\nВыберите количество:", kb_amounts())

    elif data.startswith("amount_") and data != "amount_custom":
        stars = int(data.split("_")[1])
        price = calc_price(stars)
        await state.update_data(stars=stars, price=price)
        await replace(
            f"⭐️ Выбранное количество: <b>{stars} Stars</b>\n\n"
            f"💰 Стоимость: <b>{price:,.2f} ₽</b>\n\n"
            f"Выберите метод оплаты 👇",
            kb_payment()
        )

    elif data == "amount_custom":
        rec = sd.get("recipient", "")
        await del_msg(bot, chat, last)
        sent = await bot.send_message(
            chat,
            f"Введите количество Stars для @{rec}\n(минимум 50, максимум 1000 за раз)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("◀️ Назад", "back_amounts", EMO_BACK)]
            ])
        )
        await state.update_data(last_bot_msg=sent.message_id)
        await state.set_state(St.waiting_stars)

    # ── Оплата ────────────────────────────────────────────────────────────
    elif data == "stars_sbp":
        await call.answer("💸 СБП — жду подтверждения от lava.ru", show_alert=True)

    # ── Админ-панель ──────────────────────────────────────────────────────
    elif data == "admin_panel":
        if not is_admin(uid):
            return
        await replace("🛠 <b>Панель администратора</b>", kb_admin(uid))

    elif data == "admin_stats":
        if not is_admin(uid):
            return
        stats = get_stats()
        if not stats:
            await replace("📊 <b>Статистика</b>\n\nПокупок пока нет.", kb_admin_back())
        else:
            await replace("📊 <b>Статистика</b>\n\nВыберите пользователя:", kb_stats_users(stats))

    elif data.startswith("stat_user_"):
        if not is_admin(uid):
            return
        target_uid = data[len("stat_user_"):]
        stats = get_stats()
        info  = stats.get(target_uid)
        if not info:
            await replace("❌ Данные не найдены.", kb_admin_back())
            return
        uname     = info.get("username", "None")
        purchases = info.get("purchases", [])  # уже от старых к новым
        lines = [f"👤 <b>@{uname}</b> (ID: <code>{target_uid}</code>)\n"]
        for i, p in enumerate(purchases, 1):
            lines.append(
                f"<b>#{i}</b> {p['date']}\n"
                f"  ├ Получатель: @{p['recipient']}\n"
                f"  ├ Звёзды: {p['stars']} ⭐️\n"
                f"  ├ Сумма: {p['amount_rub']} ₽\n"
                f"  └ Метод: {p['method']}"
            )
        await replace("\n".join(lines), kb_stat_user_back())

    elif data == "admin_stop":
        if uid != OWNER_ID:
            return
        set_active(False)
        await replace(
            "🔴 <b>Бот выключен.</b>\nПользователи видят сообщение о тех. работах.",
            kb_admin(uid)
        )

    elif data == "admin_start":
        if uid != OWNER_ID:
            return
        set_active(True)
        await replace("🟢 <b>Бот включён.</b>", kb_admin(uid))

    elif data == "admin_add":
        if not is_admin(uid):
            return
        await del_msg(bot, chat, last)
        sent = await bot.send_message(
            chat,
            "Введите юзернейм нового администратора (без @):",
            reply_markup=kb_admin_back()
        )
        await state.update_data(last_bot_msg=sent.message_id)
        await state.set_state(St.waiting_add_admin)

# ──────────────────────────── FSM handlers ────────────────────────────────

async def fsm_recipient(message: Message, state: FSMContext, bot: Bot):
    uid = message.from_user.id
    if not is_active() and not is_admin(uid):
        await message.answer(MAINTENANCE_MSG)
        return

    sd = await state.get_data()
    await del_msg(bot, message.chat.id, sd.get("last_bot_msg"))
    try:
        await message.delete()
    except Exception:
        pass

    username = message.text.strip().lstrip("@")
    exists   = await check_username_exists(username)

    if not exists:
        sent = await message.answer(
            "❌ Пользователь не найден. Введите другой @username:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("◀️ Назад", "back_stars", EMO_BACK)]
            ])
        )
        await state.update_data(last_bot_msg=sent.message_id)
        await state.set_state(St.waiting_recipient)
        return

    await state.update_data(recipient=username)
    await state.set_state(None)
    sent = await message.answer(
        f"⭐️ <b>Звёзды для @{username}</b>\n\nВыберите количество:",
        reply_markup=kb_amounts(), parse_mode="HTML"
    )
    await state.update_data(last_bot_msg=sent.message_id)


async def fsm_stars(message: Message, state: FSMContext, bot: Bot):
    uid = message.from_user.id
    if not is_active() and not is_admin(uid):
        await message.answer(MAINTENANCE_MSG)
        return

    sd  = await state.get_data()
    rec = sd.get("recipient", "")
    await del_msg(bot, message.chat.id, sd.get("last_bot_msg"))
    try:
        await message.delete()
    except Exception:
        pass

    text   = message.text.strip()
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn("◀️ Назад", "back_amounts", EMO_BACK)]
    ])

    if not text.lstrip("-").isdigit():
        sent = await message.answer("❗️ Введите целое число:", reply_markup=back_kb)
        await state.update_data(last_bot_msg=sent.message_id)
        return

    stars = int(text)
    if stars < 50 or stars > 1000:
        sent = await message.answer(
            f"❗️ Введите сумму от 50 до 1000 звёзд для @{rec}", reply_markup=back_kb
        )
        await state.update_data(last_bot_msg=sent.message_id)
        return

    price = calc_price(stars)
    await state.update_data(stars=stars, price=price)
    await state.set_state(None)
    sent = await message.answer(
        f"⭐️ Выбранное количество: <b>{stars} Stars</b>\n\n"
        f"💰 Стоимость: <b>{price:,.2f} ₽</b>\n\n"
        f"Выберите метод оплаты 👇",
        reply_markup=kb_payment(), parse_mode="HTML"
    )
    await state.update_data(last_bot_msg=sent.message_id)


async def fsm_premium_recipient(message: Message, state: FSMContext, bot: Bot):
    uid = message.from_user.id
    if not is_active() and not is_admin(uid):
        await message.answer(MAINTENANCE_MSG)
        return

    sd = await state.get_data()
    await del_msg(bot, message.chat.id, sd.get("last_bot_msg"))
    try:
        await message.delete()
    except Exception:
        pass

    username = message.text.strip().lstrip("@")
    exists   = await check_username_exists(username)

    if not exists:
        sent = await message.answer(
            "❌ Пользователь не найден. Введите другой @username:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [btn("◀️ Назад", "back_premium_for", EMO_BACK)]
            ])
        )
        await state.update_data(last_bot_msg=sent.message_id)
        await state.set_state(St.waiting_premium_recipient)
        return

    await state.update_data(premium_recipient=username)
    await state.set_state(None)
    sent = await message.answer(
        f"<tg-emoji emoji-id='{EMO_PREMIUM}'>💎</tg-emoji> Premium подарок для @{username}\n\n"
        f"<tg-emoji emoji-id='{EMO_CALENDAR}'>🗓</tg-emoji> Выберите длительность подписки:",
        reply_markup=kb_premium_duration(),
        parse_mode="HTML"
    )
    await state.update_data(last_bot_msg=sent.message_id)


async def fsm_add_admin(message: Message, state: FSMContext, bot: Bot):
    sd = await state.get_data()
    await del_msg(bot, message.chat.id, sd.get("last_bot_msg"))
    try:
        await message.delete()
    except Exception:
        pass

    username = message.text.strip().lstrip("@")

    # Пробуем получить ID через get_chat
    try:
        chat_obj = await bot.get_chat(f"@{username}")
        new_id   = chat_obj.id
    except Exception:
        sent = await message.answer(
            "❌ Не удалось найти пользователя. Убедитесь что он писал боту хотя бы раз.",
            reply_markup=kb_admin_back()
        )
        await state.update_data(last_bot_msg=sent.message_id)
        return

    admins = get_admins()
    if new_id not in admins:
        admins.append(new_id)
        save_admins(admins)
        text_out = f"✅ Администратор @{username} (ID: <code>{new_id}</code>) добавлен."
    else:
        text_out = f"ℹ️ @{username} уже является администратором."

    await state.set_state(None)
    sent = await message.answer(text_out, reply_markup=kb_admin_back(), parse_mode="HTML")
    await state.update_data(last_bot_msg=sent.message_id)

# ──────────────────────────── main ────────────────────────────────────────

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start,      Command("start"))
    dp.callback_query.register(handle_callback)
    dp.message.register(fsm_recipient,  St.waiting_recipient)
    dp.message.register(fsm_stars,      St.waiting_stars)
    dp.message.register(fsm_add_admin,           St.waiting_add_admin)
    dp.message.register(fsm_premium_recipient,    St.waiting_premium_recipient)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
