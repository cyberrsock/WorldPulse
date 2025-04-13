from implementation.parser import *
from implementation.MongoDBManager import MongoDBManager

import time, requests


async def run_parser():
    while True:
        mongo = MongoDBManager()
        # мб поменять на бд?
        channels_data = load_channels()

        result = await single_call(channels_data)
        if not result.get("success"):
            print(f"ERROR WHILE PARSING WITH RETRIES {result.get('retries', 0)}...")
            await asyncio.sleep(30)
            continue

        for channel_id, parsed_data in result['news'].items():
            # Берём оригинальное название канала из channels_data
            original_channel_name = channels_data.get(channel_id, {}).get('channel_name')

            for new in parsed_data.get('news', []):
                ml_response = requests.post(
                    'http://ml-processor:8080/ml-processor/new_news',
                    json={"text": new['msg']}
                )
                print(ml_response)
                if ml_response.status_code != 200:
                    print(f"ML Error: {ml_response.text}")
                    continue
                try:
                    ml_data = ml_response.json()
                except Exception:
                    print("Invalid JSON response from ML service")
                    continue
                print(ml_data["id"], ml_data["text"], ml_data["classes"])
                ml_data["id"] = str(ml_data["id"])

                # Используем original_channel_name вместо parsed_data['channel_name']
                mongo.add_news(
                    channel=original_channel_name,
                    msg_id=new['msg_id'],
                    msg=new['msg'],
                    time=new['time']
                )

                cluster_payload = {
                    "id": str(ml_data["id"]),
                    "text": ml_data["text"],
                    "embedding": ml_data["embedding"],
                    "classes": ml_data["classes"],
                    "msg_id": new["msg_id"],
                    "time": new["time"],
                    "channel_name": original_channel_name  # Добавляем имя канала и в кластер
                }

                mongo.add_or_update_clusterized_news(cluster_payload)

        await asyncio.sleep(300)
