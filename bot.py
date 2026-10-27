#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhoneOSINT Bot v2.0 — Расширенный OSINT поиск
✅ Только легальные публичные источники
✅ Проверка в базах утечек (ссылки)
✅ Поиск по номеру, username, email
✅ Максимум открытых данных
"""

import os
import re
import time
import logging
from collections import defaultdict

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
_last_call = defaultdict(float)

# ==================== ТИПИЗАЦИЯ НОМЕРОВ ====================

TYPE_MAP = {
    phonenumbers.PhoneNumberType.MOBILE: "мобильный",
    phonenumbers.PhoneNumberType.FIXED_LINE: "стационарный",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "стационарный / мобильный",
    phonenumbers.PhoneNumberType.TOLL_FREE: "бесплатный (800)",
    phonenumbers.PhoneNumberType.VOIP: "VoIP",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "премиум",
    phonenumbers.PhoneNumberType.UNKNOWN: "неизвестно",
}

# ==================== ИЗВЛЕЧЕНИЕ ДАННЫХ ====================

def extract_numbers(text):
    """Извлекает все номера из текста"""
    pattern = r'\+?\d{9,15}'
    matches = re.findall(pattern, text)
    numbers = []
    for m in matches:
        clean = re.sub(r'\D', '', m)
        if 10 <= len(clean) <= 15:
            numbers.append(m)
    return list(set(numbers))

def find_number(text):
    """Пытается распарсить номер из произвольного текста"""
    digits = re.sub(r"\D", "", text)
    
    if len(digits) < 10 or len(digits) > 17:
        return None
    
    regions = ["RU", "UA", "KZ", "BY", "US", "GB", "DE", "FR", "PL", "TR", "IL", "AE", "CN", "IN"]
    
    for region in regions:
        try:
            candidate = phonenumbers.parse("+" + digits, region)
            if phonenumbers.is_valid_number(candidate):
                return candidate
        except:
            continue
    
    try:
        candidate = phonenumbers.parse("+" + digits, None)
        if phonenumbers.is_possible_number(candidate):
            return candidate
    except:
        pass
    
    return None

def extract_telegram_username(text):
    """Ищет @username в тексте"""
    pattern = r'@([a-zA-Z0-9_]{5,32})'
    matches = re.findall(pattern, text)
    return matches[0] if matches else None

def parse_tg_profile_url(text):
    """Извлекает юзернейм из ссылки t.me/username"""
    pattern = r't\.me/([a-zA-Z0-9_]{5,32})(?:\?| |$)'
    matches = re.findall(pattern, text.lower())
    return matches[0] if matches else None

# ==================== БАЗОВАЯ ИНФО ====================

def esc(value):
    """Экранирование под HTML"""
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def basic_phone_info(n):
    """Базовая информация о номере"""
    intl = phonenumbers.format_number(n, phonenumbers.International)
    national = phonenumbers.format_number(n, phonenumbers.National)
    e164 = phonenumbers.format_number(n, phonenumbers.E164)
    
    country = geocoder.country_name_for_number(n, "ru") or "неизвестно"
    region_code = phonenumbers.region_code_for_number(n) or "??"
    area = geocoder.description_for_number(n, "ru") or "—"
    operator = carrier.name_for_number(n, "ru") or "не определён"
    zones = ", ".join(timezone.time_zones_for_number(n)) or "—"
    line_type = TYPE_MAP.get(phonenumbers.number_type(n), "неизвестно")
    valid = "да" if phonenumbers.is_valid_number(n) else "нет"
    
    return {
        "intl": intl, "national": national, "e164": e164,
        "country": country, "region_code": region_code,
        "area": area, "operator": operator, "zones": zones,
        "line_type": line_type, "valid": valid,
        "clean": e164.lstrip("+")
    }

# ==================== ОТЧЁТЫ ====================

def build_phone_report(info):
    """Формирует текст отчёта о номере"""
    return (
        f"📱 <b>Анализ номера</b>\n\n"
        f"<b>Международный:</b> <code>{esc(info['intl'])}</code>\n"
        f"<b>Национальный:</b> <code>{esc(info['national'])}</code>\n"
        f"<b>E.164:</b> <code>{esc(info['e164'])}</code>\n\n"
        f"🌍 <b>Страна:</b> {esc(info['country'])} ({esc(info['region_code'])})\n"
        f"📍 <b>Регион:</b> {esc(info['area'])}\n"
        f"📡 <b>Оператор:</b> {esc(info['operator'])}\n"
        f"☎️ <b>Тип линии:</b> {esc(info['line_type'])}\n"
        f"🕐 <b>Часовой пояс:</b> {esc(info['zones'])}\n"
        f"✅ <b>Валидный:</b> {esc(info['valid'])}\n\n"
        f"🔍 <b>Поиск в интернете:</b>"
    )

def build_tg_report(username):
    """Формирует отчёт по юзернейму Telegram"""
    profile_link = f"https://t.me/{username}"
    
    return (
        f"💬 <b>Telegram профиль</b>\n\n"
        f"<b>Юзернейм:</b> @{esc(username)}\n"
        f"<b>Профиль:</b> {profile_link}\n\n"
        f"🔍 <b>Поиск в интернете:</b>"
    )

def build_email_report(email):
    """Формирует отчёт по email для проверки в утечках"""
    encoded_email = email.replace("@", "%40")
    
    return (
        f"📧 <b>Email OSINT</b>\n\n"
        f"<code>{esc(email)}</code>\n\n"
        f"<b>Проверка в базах утечек:</b>\n"
        f"<i>Нажми на сервисы ниже для ручной проверки</i>"
    )

# ==================== ССЫЛКИ ДЛЯ ПОИСКА ====================

def phone_search_links(info):
    """Генерирует поисковые ссылки для номера"""
    e164 = info["e164"]
    digits = info["clean"]
    quoted = f"%22{e164}%22"
    
    links = {
        "Google E164": f"https://www.google.com/search?q={quoted}",
        "Google чистый": f"https://www.google.com/search?q=\"{digits}\"",
        "Яндекс": f"https://yandex.ru/search/?text={quoted}",
        "Яндекс Avito": f"https://yandex.ru/search/?text=\"{e164} сайт:avito.ru\"",
        "Avito": f"https://www.avito.ru/all?q={digits}",
        "OLX": f"https://www.olx.ua/ad/q-{digits}/",
        "VK": f"https://vk.com/search?c%5Bq%5D={digits}",
        "OK": f"https://www.ok.ru/search/people?q={digits}",
        "Facebook": f"https://www.facebook.com/search/top?q={digits}",
        "Truecaller": f"https://www.truecaller.com/search/ru/{digits}",
        "NumLookup": f"https://numlookup.com/?v={digits}",
        "WhoCalledMe": f"https://www.whocalledmetelecom.co.uk/search/{digits}",
        "Telegram": f"https://t.me/+{digits}",
        "WhatsApp": f"https://wa.me/{digits}",
        "Viber": f"viber://chat?number=%2B{digits}",
        "Signal": f"https://signal.me/#p/+{digits}",
    }
    
    return links

def email_breach_search(email):
    """Генерирует ссылки для проверки email в утечках"""
    encoded_email = email.replace("@", "%40").replace(".", "%2E")
    
    links = {
        "HaveIBeenPwned": f"https://haveibeenpwned.com/account/{esc(email)}",
        "DeHashed": f"https://dehashed.com/search?query={esc(email)}",
        "LeakCheck": f"https://leakcheck.io/?q={esc(email)}",
        "IntelX": f"https://intelx.io/?s={encoded_email}&t=email",
        "Firefox Monitor": f"https://monitor.firefox.com/?email={esc(email)}",
        "Google Password Checkup": f"https://passwords.google.com/check/password?email={esc(email)}",
    }
    
    return links

def tg_search_links(username):
    """Генерирует ссылки для поиска юзернейма"""
    escaped = username.replace(" ", "%20")
    
    links = {
        "Telegram": f"https://t.me/{username}",
        "Google": f"https://www.google.com/search?q=\"@{username}\"",
        "Яндекс": f"https://yandex.ru/search/?text=\"@{username}\"",
        "Google Images": f"https://www.google.com/search?tbm=isch&q=\"@{username}\"",
        "TgStat": f"https://tgstat.ru/search?q={escaped}",
        "Telemetr": f"https://telemetr.me/search?q={escaped}",
        "Telegram Channels": f"https://telegram.org/dl/search?q={escaped}",
    }
    
    return links

def username_osint(username):
    """Ссылки для OSINT по юзернейму across platforms"""
    encoded = username.replace(" ", "%20")
    
    links = {
        "Google": f"https://www.google.com/search?q=\"@{username}\"",
        "Social Searcher": f"https://www.social-searcher.com/media-search/?q={encoded}",
        "Namechk": f"https://namechk.com/{username}",
        "KnowEm": f"https://knowem.com/check_usernames.php?search={username}",
        "Sherlock (GitHub)": f"https://github.com/sherlock-project/sherlock",
        "WhatsMyName": f"https://whatsmyname.app/@{username}",
        "UserSearch": f"https://usersearch.org/?q=@{username}",
    }
    
    return links

# ==================== ПУБЛИЧНЫЕ РЕСУРСЫ ====================

def public_resources():
    """Список публичных OSINT ресурсов"""
    return {
        "Have I Been Pwned": "https://haveibeenpwned.com/",
        "DeHashed": "https://dehashed.com/",
        "IntelX": "https://intelx.io/",
        "LeakCheck": "https://leakcheck.io/",
        "Epieos": "https://epieos.com/",
        "Maltego": "https://www.maltego.com/",
        "SpiderFoot": "https://www.spiderfoot.net/",
        "OSINT Framework": "https://osintframework.com/",
    }

def build_keyboard(links):
    """Создаёт инлайн-клавиатуру из словаря ссылок"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    buttons = []
    for name, url in list(links.items()):
        buttons.append(InlineKeyboardButton(name, url=url))
    
    kb.add(*buttons)
    return kb

# ==================== ОБРАБОТЧИКИ ====================

@bot.message_handler(commands=["start"])
def cmd_start(message):
    welcome = (
        "🤖 <b>PhoneOSINT Bot v2.0</b>\n\n"
        "✅ Только легальные публичные источники\n\n"
        "<i>Отправь:</i>\n"
        "• 📱 <code>+79991234567</code> — анализ номера\n"
        "• 💬 <code>@username</code> — поиск по Telegram\n"
        "• 📧 <code>user@example.com</code> — проверка в утечках\n\n"
        "/help — справки\n"
        "/about — о боте\n"
        "/sources — список ресурсов"
    )
    bot.send_message(message.chat.id, welcome)

@bot.message_handler(commands=["help"])
def cmd_help(message):
    help_text = (
        "📋 <b>Команды:</b>\n\n"
        "/start — приветствие\n"
        "/about — о боте и ограничениях\n"
        "/sources — список OSINT ресурсов\n"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=["about"])
def cmd_about(message):
    about_text = (
        "ℹ️ <b>Что умеет бот:</b>\n\n"
        "✅ Анализ номера (страна, оператор, регион)\n"
        "✅ Поиск упоминаний в интернете\n"
        "✅ Поиск по Telegram username\n"
        "✅ Проверка email в базах утечек (ссылки)\n"
        "✅ OSINT по username (соцсети)\n\n"
        "<b>Что НЕдоступно:</b>\n\n"
        "❌ ФИО, адрес, паспортные данные\n"
        "❌ Геолокация в реальном времени\n"
        "❌ История звонков/SMS\n"
        "❌ Приватные данные из закрытых баз\n\n"
        "<i>Все данные из публичных источников.</i>"
    )
    bot.send_message(message.chat.id, about_text)

@bot.message_handler(commands=["sources"])
def cmd_sources(message):
    sources = public_resources()
    text = "🔗 <b>OSINT ресурсы:</b>\n\n"
    for name, url in sources.items():
        text += f"• <a href='{url}'>{name}</a>\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.from_user.id
    
    # Антифлуд
    now = time.time()
    if now - _last_call[user_id] < 5:
        bot.reply_to(message, "⏳ Подожди пару секунд.")
        return
    _last_call[user_id] = now
    
    text = message.text.strip()
    response_parts = []
    
    # 1. Поиск номеров
    numbers = extract_numbers(text)
    for num in numbers:
        parsed = find_number(num)
        if parsed:
            info = basic_phone_info(parsed)
            report = build_phone_report(info)
            response_parts.append((report, phone_search_links(info)))
    
    # 2. Поиск Telegram username
    username = extract_telegram_username(text) or parse_tg_profile_url(text)
    if username:
        report = build_tg_report(username)
        response_parts.append((report, tg_search_links(username)))
        # Дополнительно — OSINT по юзернейму
        response_parts.append(("🔍 <b>OSINT по username:</b>", username_osint(username)))
    
    # 3. Поиск email (в утечках)
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        email = email_match.group()
        report = build_email_report(email)
        links = email_breach_search(email)
        response_parts.append((report, links))
    
    if not response_parts:
        bot.reply_to(message, (
            "❓ Не понял запрос.\n\n"
            "Отправь:\n"
            "• 📱 Номер: <code>+79991234567</code>\n"
            "• 💬 Username: <code>@username</code>\n"
            "• 📧 Email: <code>test@example.com</code>"
        ))
        return
    
    # Отправляем ответы
    for i, (report, links) in enumerate(response_parts):
        if links:
            kb = build_keyboard(links)
            bot.reply_to(message, report, reply_markup=kb)
        else:
            bot.reply_to(message, report)
    
    logging.info("Обработан запрос от user %s", user_id)

# ==================== ЗАПУСК ====================

if __name__ == "__main__":
    logging.info("🤖 Бот запущен v2.0...")
    bot.infinity_polling(timeout=30, long_polling_timeout=25)
