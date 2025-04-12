from parser import *
from MongoDBManager import MongoDBManager

import time, requests


while True:
    mongo = MongoDBManager()
    # мб поменять на бд?
    channels_data = load_channels()

    result = client.loop.run_until_complete(single_call(channels_data))
    if result["success"] is False:
        print(f"ERROR WHILE PARSING WITH RETRIES {result['retries']}...")
        time.sleep(30)
        continue

    for channel in result['news']:
        for new in channel['news']:
            ml_result = requests.post('/ml-processor/new_news', json={"text": new['msg']})
            print(ml_result.json())
            # ml_result = {
            #     "id": -1,  # или ObjectId существующего
            #     "text": "Aboba123",
            #     "embedding": "aEicASWpdad89",
            #     "classes": ["Экономика", "Внешняя политика"]
            # }

            mongo.add_news(channel['channel_name'], new['msg_id'], new['msg'], new['time'])

            cluster_payload = {
                "id": ml_result["id"],
                "text": ml_result["text"],
                "embedding": ml_result["embedding"],
                "classes": ml_result["classes"],
                "msg_id": new["msg_id"],
                "time": new["time"],
            }

            mongo.add_or_update_clusterized_news(cluster_payload)

    time.sleep(300)
