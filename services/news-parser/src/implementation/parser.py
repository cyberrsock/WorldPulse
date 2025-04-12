import os, json, asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient, errors


# Получаем API-ключи из переменных окружения
api_id = int(os.getenv('TG_API_ID', 20673875))
api_hash = os.getenv('TG_API_HASH', "1e923d38dca961ed878ca85b0c03abdb")
print(f"App started with API ID: {api_id}")

# Инициализация TelegramClient
client = TelegramClient('tg_parser', api_id, api_hash)

# Файл с настройками каналов
channels_file = "tg_channels.json"
# Файл для логов
log_filename = "log.txt"
# Лимит постов за один запрос
limit_per_request = int(os.getenv('LIMIT_POSTS_PER_ONE_REQUEST', 20))

# Создаем (очищаем) файл логов
with open(log_filename, 'w', encoding='utf-8'):
    pass

client = TelegramClient('session', api_id, api_hash)
async def init_client():
    await client.start()

async def safe_get_messages(chan_id, limit):
    try:
        messages = await client.get_messages(chan_id, limit=limit)
        return messages
    except Exception as e:
        print(f"Ошибка подключения: {e}. Переподключаемся...")
        await client.disconnect()
        await client.connect()
        return await safe_get_messages(chan_id, limit)


def convert_to_local_time(dt):
    """Преобразует время из UTC в UTC+3."""
    return dt.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=3)))


def save_messages_to_file(channel_name, messages):
    """Сохраняет список сообщений в файл."""
    with open(log_filename, 'a', encoding='utf-8') as file:
        file.write(f"\n{'*' * 40}\nSource: {channel_name}\n")
        for msg in messages:
            file.write(f"{'-' * 40}\nTime: {msg.date}, Message: {msg.message}\n")


def load_channels(filename=channels_file):
    """Загружает данные каналов из JSON-файла."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки файла {filename}: {e}")
        return {}


def save_channels(channels_data, filename=channels_file):
    """Сохраняет данные каналов в JSON-файл."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(channels_data, f, ensure_ascii=False, indent=2)


async def fetch_news_since(channels_data, limit=limit_per_request):
    """
    Собирает новости для каждого канала, у которых msg_id больше last_detected_id.

    :param channels_data: словарь, ключами которого являются id канала (в виде строки),
                          а значениями – словари с информацией: channel_name, last_sent_id, last_detected_id.
    :param limit: лимит сообщений для запроса.
    :return: обновленный словарь вида:
             { channel_id: { "channel_name": ..., "news": [новости], "last_detected_id": новый_id }, ... }
             Каждая новость – словарь с ключами: msg_id, msg, time.
    """

    if not client.is_connected():
        await client.connect()
    result = {}
    for chan_id_str, info in channels_data.items():
        chan_id = int(chan_id_str)
        channel_name = info.get("channel_name", "Неизвестно")
        last_detected = info.get("last_detected_id", 0)
        # Получаем сообщения
        messages = await safe_get_messages(chan_id, limit=limit)
        for msg in messages:
            msg.date = convert_to_local_time(msg.date)
        # Фильтруем только новые сообщения
        new_messages = [
            {"msg_id": msg.id, "msg": msg.message, "time": msg.date.isoformat()}
            for msg in messages if msg.id > last_detected
        ]
        # Определяем новый максимальный id, если есть новые сообщения
        new_max_id = max([msg["msg_id"] for msg in new_messages], default=last_detected)
        result[chan_id_str] = {
            "channel_name": channel_name,
            "news": new_messages,
            "last_detected_id": new_max_id
        }
        # Сохраняем лог сообщений
        save_messages_to_file(channel_name, messages)
    return result


async def single_call(channels_data, retries=3, timeout=10):
    """
    Запускает сбор новостей с обработкой ошибок.

    :param channels_data: словарь с информацией о каналах.
    :param retries: число попыток.
    :param timeout: таймаут одного вызова.
    :return: словарь со структурой:
             {
               "success": bool,
               "news": { channel_id: { "channel_name": ..., "news": [...], "last_detected_id": ... }, ... },
               "time": время выполнения (сек),
               "retries": количество попыток
             }
    """
    await init_client()
    start_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    for attempt in range(retries):
        try:
            news = await asyncio.wait_for(fetch_news_since(channels_data), timeout=timeout)
            end_time = datetime.utcnow().replace(tzinfo=timezone.utc)
            return {
                "success": True,
                "time": (end_time - start_time).total_seconds(),
                "retries": attempt + 1,
                "news": news
            }
        except (errors.FloodWaitError, errors.ServerError, asyncio.TimeoutError) as e:
            print(f"[Ошибка] Попытка {attempt + 1} из {retries}: {e}")
            await asyncio.sleep(5)
    end_time = datetime.utcnow().replace(tzinfo=timezone.utc)
    return {
        "success": False,
        "time": (end_time - start_time).total_seconds(),
        "retries": retries,
        "news": {}
    }


async def periodic_news_fetcher(interval_minutes=1):
    """
    Периодически собирает новости.

    Загружает данные из tg_channels.json, вызывает single_call, обновляет last_detected_id для каждого канала,
    сохраняет изменения и выводит на экран последний msg_id для каждого канала.
    """
    channels_data = load_channels()
    while True:
        print("Запуск сбора новостей...")
        result = await single_call(channels_data)
        if result["success"]:
            news = result["news"]
            # Обновляем last_detected_id в channels_data для каждого канала
            for chan_id, info in news.items():
                if info["news"]:
                    new_max = info["last_detected_id"]
                    channels_data[chan_id]["last_detected_id"] = max(channels_data[chan_id].get("last_detected_id", 0),
                                                                     new_max)
                    print(
                        f"Канал: {channels_data[chan_id]['channel_name']}. Последний msg_id: {channels_data[chan_id]['last_detected_id']}")
                else:
                    print(f"Канал: {channels_data[chan_id]['channel_name']}. Нет новых новостей.")
            # Сохраняем обновленные данные в файл
            save_channels(channels_data)
        else:
            print("Ошибка сбора новостей.")
        # Ждем интервал
        await asyncio.sleep(interval_minutes * 60)


if __name__ == '__main__':
    with client:
        # Пример одиночного вызова:
        channels_data = load_channels()
        result = client.loop.run_until_complete(single_call(channels_data))
        print("Результат single_call:")
        print(result)

        # Запуск периодического сбора новостей (каждую 1 минуту)
        print("Запуск периодического сбора новостей (каждую 1 минуту)...")
        client.loop.run_until_complete(periodic_news_fetcher(interval_minutes=1))
