from implementation.parser import *
from implementation.MongoDBManager import MongoDBManager
import ml_processor_client

import time, requests

def make_client(lib, host):
    api_client = lib.ApiClient(lib.Configuration(host=host))
    return lib.DefaultApi(api_client)

ml_client = make_client(ml_processor_client, 'http://ml-processor:8080')

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
                if new.strip() == "":
                    continue
                try:
                    ml_data = ml_client.ml_processor_new_news_post(ml_processor_client.MlProcessorNewNewsPostRequest(text=new['msg'])).to_dict()
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
