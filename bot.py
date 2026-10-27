#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import time
from collections import defaultdict

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import phonenumbers
from phonenumbers import geocoder, carrier, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN!")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
_last_call = defaultdict(float)

TYPE_MAP = {
    phonenumbers.PhoneNumberType.MOBILE: "мобильный",
    phonenumbers.PhoneNumberType.FIXED_LINE: "стационарный",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "стационарный / мобильный",
    phonenumbers.PhoneNumberType.TOLL_FREE: "бесплатный (800)",
    phonenumbers.PhoneNumberType.VOIP: "VoIP",
    phonenumbers.PhoneNumberType.UNKNOWN: "неизвестно",
}

def find_number(text):
    import re
    digits = re.sub(r"\D", "", text)
    if len(digits) < 10 or len(digits) > 17:
        return None
    for region in ["RU", "UA", "KZ", "BY", "US", "GB", "DE"]:
        try:
            candidate = phonenumbers.parse("+" + digits, region)
        except:
            continue
        if phonenumbers.is_valid_number(candidate):
            return candidate
    try:
        candidate = phonenumbers.parse("+" + digits, None)
        if phonenumbers.is_possible_number(candidate):
            return candidate
    except:
        pass
    return None

def esc(v):
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_report(n):
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
    
    return (
        f"📱 <b>Результат анализа</b>\n\n"
        f"<b>Международный:</b> <code>{esc(intl)}</code>\n"
        f"<b>Национальный:</b> <code>{esc(national)}</code>\n"
        f"<b>E.164:</b> <code>{esc(e164)}</code>\n\n"
        f"🌍 <b>Страна:</b> {esc(country)} ({esc(region_code)})\n"
        f"📍 <b>Регион:</b> {esc(area)}\n"
        f"📡 <b>Оператор:</b> {esc(operator)}\n"
        f"☎️ <b>Тип линии:</b> {esc(line_type)}\n"
        f"🕐 <b>Часовой пояс:</b> {esc(zones)}\n"
        f"✅ <b>Валидный:</b> {esc(valid)}\n\n"
        "👇 Кнопки ниже — для ручной проверки."
    )

def build_keyboard(n):
    e164 = phonenumbers.format_number(n, phonenumbers.E164)
    digits = e164.lstrip("+")
    quoted = f"%22{e164}%22"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔍 Google", url=f"https://www.google.com/search?q={quoted}"),
        InlineKeyboardButton("🔍 Яндекс", url=f"https://yandex.ru/search/?text={quoted}"),
        InlineKeyboardButton("🛒 Avito", url=f"https://www.avito.ru/all?q={digits}"),
        InlineKeyboardButton("👤 VK", url=f"https://vk.com/search?c%5Bq%5D={digits}"),
        InlineKeyboardButton("✈️ Telegram", url=f"https://t.me/+{digits}"),
    )
    return kb

@bot.message_handler(commands=["start"])
def cmd_start(message):
    bot.send_message(message.chat.id, 
        "📱 <b>Phone OSINT Bot</b>\n\n"
        "Отправь номер телефона — получишь разбор по публичным данным.\n"
        "Формат любой: +79991234567, 89991234567")

@bot.message_handler(content_types=["text"])
def handle_text(message):
    user_id = message.from_user.id
    now = time.time()
    if now - _last_call[user_id] < 5:
        bot.reply_to(message, "⏳ Подожди пару секунд.")
        return
    _last_call[user_id] = now
    
    number = find_number(message.text or "")
    if number is None:
        bot.reply_to(message, "❓ Не похоже на номер телефона.\nПример: <code>+79991234567</code>")
        return
    
    try:
        bot.send_chat_action(message.chat.id, "typing")
        bot.reply_to(message, build_report(number), reply_markup=build_keyboard(number))
        logging.info("Обработан номер %s (user %s)", number, user_id)
    except Exception as exc:
        logging.exception("Ошибка обработки")
        bot.reply_to(message, f"⚠️ Ошибка: <code>{esc(exc)}</code>")

if __name__ == "__main__":
    logging.info("Бот запущен...")
    bot.infinity_polling(timeout=30, long_polling_timeout=25)
