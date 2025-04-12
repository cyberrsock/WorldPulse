import datetime, time
import asyncio
from datetime import datetime as dt
import telegram_bot_client
from implementation.MongoContext import MongoDBManager

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

# Фиктивные данные для документов в коллекции news
# Ключ – msg_id, значение – информация о новости (канал, контент, время публикации)
today_str = dt.now().strftime("%Y-%m-%d")

# Фиктивные данные для кластеризованных новостей (clusterized_news)
# В документах присутствуют поля:
# description, classes, список идентификаторов новостей (news_ids),
# first_time и last_time (в виде ISO-строк)


def parse_time(time_str: str) -> dt:
    # time_str — строка в формате "HH:MM", комбинируем с сегодняшней датой
    return dt.strptime(today_str + "T" + time_str + ":00", "%Y-%m-%dT%H:%M:%S")


def process_mailing():
    mongo_manager = MongoDBManager()
    now = dt.now()
    print(f"Текущее время: {now.strftime('%H:%M:%S')}")

    # Получаем данные из MongoDB
    news_data = mongo_manager.get_news_dict()
    clusterized_news = mongo_manager.get_clusterized_news()
    users = mongo_manager.get_users()

    # Маппинг weekday для русского расписания:
    day_mapping = {
        0: "Пн",
        1: "Вт",
        2: "Ср",
        3: "Чт",
        4: "Пт",
        5: "Сб",
        6: "Вс"
    }
    today_key = day_mapping[now.weekday()]

    for user in users:
        user_id = user["_id"]
        settings = user["settings"]
        # Получаем расписание именно для текущего дня
        user_schedule = settings.get("schedule", {})
        day_schedule = user_schedule.get(today_key)
        if not day_schedule:
            print(f"Пользователь {user_id}: Нет расписания для сегодня ({today_key}).")
            continue

        # Для категорий и источников предполагаем, что они хранятся как идентификаторы
        categories = [cat["id"] for cat in settings.get("categories", [])]
        sources = settings.get("sources", [])

        # Время последней рассылки
        try:
            last_sending = parse_time(settings["last_sending"])
        except Exception as e:
            print(f"Пользователь {user_id}: Ошибка парсинга времени последней рассылки – {e}")
            continue

        # Преобразуем расписание для текущего дня (каждый элемент типа "10:00:00")
        schedule_times = []
        for t in day_schedule:
            try:
                st = parse_time(t)
                if st > last_sending:
                    schedule_times.append(st)
            except Exception as e:
                print(f"Пользователь {user_id}: Неверный формат расписания {t} – {e}")
                continue

        if not schedule_times:
            print(f"Пользователь {user_id}: Нет будущих расписаний после последней рассылки.")
            continue

        next_schedule = min(schedule_times)
        # Если ближайшее расписанное время уже настало
        if next_schedule <= now:
            print(f"Пользователь {user_id}: Пора рассылать (ближайшее расписание: {next_schedule.strftime('%H:%M:%S')}).")
            msg = ""
            # Фильтруем кластеры:
            for cluster in clusterized_news:
                cluster_last_time = dt.strptime(cluster["last_time"], "%Y-%m-%dT%H:%M:%S")
                # Проверяем, что кластер свежий и хотя бы одна категория присутствует
                if cluster_last_time < last_sending or not any(cat in categories for cat in cluster['classes']):
                    continue

                # Из кластера собираем каналы по новостям
                channels_in_cluster = set()
                for msg_id in cluster["news_ids"]:
                    news_doc = news_data.get(str(msg_id))
                    if news_doc:
                        channels_in_cluster.add(news_doc["channel"])

                # Пропускаем кластер, если ни один из каналов не входит в источники пользователя
                if not any(ch in sources for ch in channels_in_cluster):
                    continue

                msg += f"{cluster['description']} (Каналы: {', '.join(channels_in_cluster)})\n"

            if msg:
                send_message(user_id, msg)
                # Здесь можно обновить время последней рассылки в БД, если требуется
                settings["last_sending"] = now.strftime("%H:%M:%S")
            else:
                print(f"Пользователь {user_id}: Нет новостей для рассылки.")
        else:
            print(f"Пользователь {user_id}: Еще не время. Ближайшее расписание: {next_schedule.strftime('%H:%M:%S')}")


# Мега базированный способ ожидать по 5 минут
async def run():
    print("Started news sender")
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
