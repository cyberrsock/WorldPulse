import datetime, time
import asyncio
from datetime import datetime as dt, timedelta, timezone
import telegram_bot_client
from implementation.MongoContext import MongoDBManager
import logging

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
    """Парсит время в формате HH:MM или HH:MM:SS"""
    try:
        # Пробуем парсить с секундами
        return dt.strptime(today_str + "T" + time_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        try:
            # Если не получилось, пробуем без секунд
            return dt.strptime(today_str + "T" + time_str + ":00", "%Y-%m-%dT%H:%M:%S")
        except ValueError as e:
            print(f"Ошибка парсинга времени '{time_str}': {e}")
            return dt.now()  # Возвращаем текущее время как fallback


def process_mailing():
    mongo_manager = MongoDBManager()
    tz = timezone(timedelta(hours=3))
    now = dt.now(tz)
    print(f"Текущее время: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    news_data = mongo_manager.get_news_dict()
    clusterized_news = mongo_manager.get_clusterized_news()
    users = mongo_manager.get_users()
    all_categories = mongo_manager.get_categories()
    all_sources = mongo_manager.get_sources()
    print(f"All sources: {all_sources}")

    day_mapping = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
    today_key = day_mapping[now.weekday()]

    for user in users:
        user_id = user["_id"]
        settings = user.get("settings", {})
        user_schedule = settings.get("schedule", {})
        day_schedule = user_schedule.get(today_key)
        if not day_schedule:
            print(f"Пользователь {user_id}: Нет расписания на сегодня ({today_key}).")
            continue
        print(f"Пользователь {user_id}, расписание {day_schedule}")

        user_category_ids = [str(cat["id"]) for cat in settings.get("categories", [])]
        raw_categories = [
            all_categories[cat_id]
            for cat_id in user_category_ids
            if cat_id in all_categories
        ]
        categories = [cat['name'] for cat in raw_categories]
        user_source_ids = list(map(str, settings.get("sources", [])))
        print(f"User source ids: {user_source_ids}")
        sources = [
            all_sources[src_id]
            for src_id in user_source_ids
            if src_id in all_sources
        ]

        # Парсинг last_sending с учётом таймзоны
        last_sending_str = settings.get("last_sending")
        if last_sending_str:
            try:
                last_sending = dt.fromisoformat(last_sending_str).astimezone(tz)
            except Exception as e:
                print(f"Пользователь {user_id}: Ошибка парсинга last_sending: {e}. Используется текущее время.")
                last_sending = dt.combine(now.date(), dt.min.time()).replace(tzinfo=tz)
        else:
            last_sending = dt.combine(now.date(), dt.min.time()).replace(tzinfo=tz)

        schedule_times = []
        for time_str in day_schedule:
            try:
                parsed_time = dt.strptime(time_str, "%H:%M:%S").time()
                schedule_dt = dt.combine(now.date(), parsed_time).replace(tzinfo=tz)
                if schedule_dt > last_sending:
                    schedule_times.append(schedule_dt)
            except Exception as e:
                print(f"Пользователь {user_id}: Неверный формат времени {time_str}: {e}")
                continue

        if not schedule_times:
            print(f"Пользователь {user_id}: Нет предстоящих рассылок после {last_sending.strftime('%H:%M:%S')}.")
            continue

        next_schedule = min(schedule_times)
        print(f"Нужно ли отправлять сообщение пользователю: {next_schedule} <= {now} ({last_sending}?")
        # Или у пользователя первое сообщение
        if next_schedule <= now or not last_sending_str:
            print(f"Пользователь {user_id}: Рассылаем. Время: {next_schedule.strftime('%H:%M:%S')}.")
            msg = ""
            for cluster in clusterized_news:
                cluster_last_time = dt.fromisoformat(cluster["last_time"]).astimezone(tz)
                print(f"cluster_last_time: {cluster_last_time}, last_sending: {last_sending}, categories: {cluster.get('classes', [])}, check_categories: {any(category_name in cluster.get('classes', []) for category_name in categories)}")
                if cluster_last_time < last_sending:
                    continue
                if not any(category_name in cluster.get('classes', []) for category_name in categories):
                    continue

                channels = set()
                print(f"Cluster ids: {cluster['news_ids']}")
                for msg_id in cluster["news_ids"]:
                    news = news_data.get(str(msg_id))
                    print(f"New: {news}")
                    if news:
                        channels.add(news["channel"])
                print(f"sources: {sources}, channels: {channels}, check_channels: {any(ch in sources for ch in channels):}")
                if not any(ch in sources for ch in channels):
                    continue

                msg += f"{cluster['description']} (Каналы: {', '.join(channels)})\n"
                print(f"Сообщение для пользователя {user_id} было обновлено, теперь его длина {len(msg)}")

            if msg:
                send_message(user_id, msg)
                mongo_manager.update_user_last_sending(user_id, now.isoformat())
            else:
                print(f"Пользователь {user_id}: Нет подходящих новостей.")
                mongo_manager.update_user_last_sending(user_id, now.isoformat())
        else:
            print(f"Пользователь {user_id}: Следующая рассылка в {next_schedule.strftime('%H:%M:%S')}.")

# Мега базированный способ ожидать по 5 минут
async def run():
    print("Started news sender")
    logging.info("Started news sender")
    while True:
        current_min = dt.now().minute
        if current_min % 2 == 0:
            process_mailing()
            await asyncio.sleep(60)
        else:
            print("Не время рассылки (ожидаем минуты, кратные 5).")
            await asyncio.sleep(5)

# if __name__ == "__main__":
#     # Симулируем работу скрипта, который запускается каждую минуту,
#     # а внутри проверяем, кратно ли время 5 минутам.
#     process_mailing()
