from implementation.parser import *
from implementation.MongoDBManager import MongoDBManager

import time, requests


async def run_parser():
    while True:
        mongo = MongoDBManager()
        # мб поменять на бд?
        channels_data = load_channels()

        result = await single_call(channels_data)
        if result["success"] is False:
            print(f"ERROR WHILE PARSING WITH RETRIES {result['retries']}...")
            time.sleep(30)
            continue

        for channel_id, parsed_data in result['news'].items():
            # Берём оригинальное название канала из channels_data
            original_channel_name = channels_data[channel_id]['channel_name']

            for new in parsed_data['news']:
                ml_result = requests.post(
                    'http://ml-processor:8080/ml-processor/new_news',
                    json={"text": new['msg']}
                )
                print(ml_result)
                print(ml_result.json())

                # Используем original_channel_name вместо parsed_data['channel_name']
                mongo.add_news(
                    channel=original_channel_name,
                    msg_id=new['msg_id'],
                    msg=new['msg'],
                    time=new['time']
                )

                cluster_payload = {
                    "id": ml_result["id"],
                    "text": ml_result["text"],
                    "embedding": ml_result["embedding"],
                    "classes": ml_result["classes"],
                    "msg_id": new["msg_id"],
                    "time": new["time"],
                    "channel_name": original_channel_name  # Добавляем имя канала и в кластер
                }

                mongo.add_or_update_clusterized_news(cluster_payload)

        await asyncio.sleep(300)
