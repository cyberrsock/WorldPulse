import datetime, time
import asyncio
from datetime import datetime as dt
import telegram_bot_client

def make_client(lib, host):
    api_client = lib.ApiClient(lib.Configuration(host=host))
    return lib.DefaultApi(api_client)

tg_client = make_client(telegram_bot_client, 'http://telegram-bot:8080')

# Функция-симуляция отправки сообщения пользователю
def send_message(user_id: int, message: str):
    global tg_client
    tg_client.send_message(telegram_bot_client.SendMessageRequest(chat_id=user_id, message_text=message))
    print(f"\n=== Отправляем сообщение пользователю {user_id} ===")
    print(message)
    print("=== Сообщение отправлено ===\n")


# Фиктивные данные для пользователей
# Каждый пользователь имеет: _id, настройки с расписанием (в виде списка строк HH:MM),
# список источников (каналов) и время последней рассылки (также HH:MM)
users = [
    {
        "_id": 1,
        "settings": {
            "schedule": ["10:00", "10:05", "10:10", "15:00"],
            "sources": ["ChannelA", "ChannelB"],
            "categories": ["Политика", "Экономика"],
            "last_sending": "10:03"
        }
    },
    {
        "_id": 2,
        "settings": {
            "schedule": ["09:55", "10:00", "10:05"],
            "sources": ["ChannelA", "ChannelC"],
            "categories": ["Экономика", "Политика"],
            "last_sending": "09:50"
        }
    }
]

# Фиктивные данные для документов в коллекции news
# Ключ – msg_id, значение – информация о новости (канал, контент, время публикации)
today_str = dt.now().strftime("%Y-%m-%d")
news_data = {
    101: {"channel": "ChannelA", "content": "Новость 101", "datetime": today_str + "T10:01:00"},
    102: {"channel": "ChannelC", "content": "Новость 102", "datetime": today_str + "T10:02:00"},
    103: {"channel": "ChannelB", "content": "Новость 103", "datetime": today_str + "T10:03:00"},
    104: {"channel": "ChannelD", "content": "Новость 104", "datetime": today_str + "T10:04:00"},
}

# Фиктивные данные для кластеризованных новостей (clusterized_news)
# В документах присутствуют поля:
# description, classes, список идентификаторов новостей (news_ids),
# first_time и last_time (в виде ISO-строк)
clusterized_news = [
    {
        "_id": "id1",
        "description": "Обновление экономики",
        "classes": ["Экономика", "Политика"],
        "news_ids": [101, 103],
        "first_time": today_str + "T10:01:00",
        "last_time": today_str + "T10:03:00"
    },
    {
        "_id": "id2",
        "description": "Политические новости",
        "classes": ["Политика"],
        "news_ids": [102, 104],
        "first_time": today_str + "T10:02:00",
        "last_time": today_str + "T10:04:00"
    }
]


def parse_time(time_str: str) -> dt:
    # time_str — строка в формате "HH:MM", комбинируем с сегодняшней датой
    return dt.strptime(today_str + "T" + time_str + ":00", "%Y-%m-%dT%H:%M:%S")


def process_mailing():
    mongo_manager = MongoDBManager()
    now = dt.now()  # текущее время
    print(f"Текущее время: {now.strftime('%H:%M')}")

    news_data = mongo_manager.get_news_dict()

    for user in users:
        user_id = user["_id"]
        settings = user["settings"]
        categories = settings["categories"]

        # Время последней рассылки пользователя (считаем, что оно за сегодня)
        try:
            last_sending = parse_time(settings["last_sending"])
        except Exception as e:
            print(f"Пользователь {user_id}: Ошибка парсинга времени последней рассылки – {e}")
            continue

        # Преобразуем расписание пользователя в datetime для сегодняшней даты
        schedule_times = []
        for t in settings["schedule"]:
            try:
                st = parse_time(t)
                if st > last_sending:  # оставляем только времена после последней рассылки
                    schedule_times.append(st)
            except Exception as e:
                print(f"Пользователь {user_id}: Неверный формат расписания {t}")
                continue

        if not schedule_times:
            print(f"Пользователь {user_id}: Нет будущих расписаний после последней рассылки.")
            continue

        next_schedule = min(schedule_times)
        # Если минимальное расписанное время находится между последней рассылкой и текущим временем, идём дальше
        if next_schedule <= now:
            print(f"Пользователь {user_id}: Пора рассылать (следующее расписание: {next_schedule.strftime('%H:%M')}).")
            msg = ""
            # Фильтруем кластеры: оставляем те, где last_time больше или равен last_sending и нужные категории
            for cluster in clusterized_news:
                cluster_last_time = dt.strptime(cluster["last_time"], "%Y-%m-%dT%H:%M:%S")
                if cluster_last_time < last_sending or not any(x in categories for x in cluster['classes']):
                    continue

                # Для каждого кластера собираем каналы по news_ids
                channels_in_cluster = set()
                for msg_id in cluster["news_ids"]:
                    news_doc = news_data.get(msg_id)
                    if news_doc:
                        channels_in_cluster.add(news_doc["channel"])

                # Если ни один из каналов не входит в источники пользователя, пропускаем кластер
                if not any(ch in settings["sources"] for ch in channels_in_cluster):
                    continue

                # Формируем сообщение: описание кластера и список каналов
                msg += f"{cluster['description']} (Каналы: {', '.join(channels_in_cluster)})\n"

            if msg:
                send_message(user_id, msg)
                # Обновляем время последней рассылки на текущее
                settings["last_sending"] = now.strftime("%H:%M")
            else:
                print(f"Пользователь {user_id}: Нет новостей для рассылки.")
        else:
            print(f"Пользователь {user_id}: Еще не время. Следующее расписание: {next_schedule.strftime('%H:%M')}")

# Мега базированный способ ожидать по 5 минут
async def run():
    while True:
        current_min = dt.now().minute
        if current_min % 5 == 0:
            process_mailing()
            await asyncio.sleep(60)
        else:
            print("Не время рассылки (ожидаем минуты, кратные 5).")
            await asyncio.sleep(5)

# if __name__ == "__main__":
#     # Симулируем работу скрипта, который запускается каждую минуту,
#     # а внутри проверяем, кратно ли время 5 минутам.
#     process_mailing()
