import json
import pathlib
import os

# Импорт нашего бота
import bot

OFFSET_FILE = pathlib.Path(".offset.json")


def load_offset():
    if OFFSET_FILE.exists():
        try:
            return json.loads(OFFSET_FILE.read_text(encoding="utf-8")).get("offset", 0)
        except Exception:
            return 0
    return 0


def save_offset(value):
    OFFSET_FILE.write_text(json.dumps({"offset": value}), encoding="utf-8")


def main():
    offset = load_offset()
    
    # Получаем новые обновления с таймаутом
    updates = bot.bot.get_updates(offset=offset, timeout=60, limit=100)
    
    for upd in updates:
        offset = upd.update_id + 1
        bot.bot.process_new_updates([upd])
    
    save_offset(offset)
    print(f"Обработано обновлений: {len(updates)}, новый offset: {offset}")


if __name__ == "__main__":
    main()
