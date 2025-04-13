from bson.binary import Binary
from bson import ObjectId
from datetime import datetime
from typing import Dict, List
import pymongo
import os
from urllib.parse import quote


class MongoDBManager:
    def __init__(self):
        self._url = "mongodb://{user}:{pw}@{hosts}/?replicaSet={rs}&authSource={auth_src}".format(
            user=quote("wpdev"),
            pw=quote(os.getenv("MONGO_PASSWORD")),
            hosts=",".join([os.getenv("MONGO_HOST")]),
            rs="rs01",
            auth_src="worldpulse",
        )

    def _get_connection(self):
        return pymongo.MongoClient(
            self._url, tls=True, tlsCAFile=".mongodb/root.crt"
        )

    def add_news(self, channel: str, msg_id: int, msg: str, time: str):
        doc = {
            "channel": channel,
            "msg_id": msg_id,
            "content": msg,
            "datetime": datetime.fromisoformat(time) if isinstance(time, str) else time,
        }
        with self._get_connection() as client:
            db = client["worldpulse"]
            db["news"].insert_one(doc)

    def add_or_update_clusterized_news(self, cluster: Dict):
        with self._get_connection() as client:
            db = client["worldpulse"]
            collection = db["clusterized_news"]

            cluster_id = cluster["id"]
            if str(cluster_id) == "":
                # создаём новый кластер
                doc = {
                    "description": cluster["text"],
                    "embedding": Binary(eval(cluster["embedding"])),
                    "classes": cluster["classes"],
                    "news_ids": [cluster["msg_id"]],
                    "first_time": datetime.fromisoformat(cluster["time"]),
                    "last_time": datetime.fromisoformat(cluster["time"]),
                }
                print(f"Try to save in clustrized_news {doc}")
                collection.insert_one(doc)
            else:
                # обновляем существующий кластер

                print(f'Try to update in clustrized_news: ' + f"{cluster_id}, {cluster['text']}, {cluster['classes']}, {datetime.fromisoformat(cluster['time'])}, {cluster["msg_id"]}")
                collection.update_one(
                    {"_id": str(cluster_id)},
                    {
                        "$set": {
                            "description": cluster["text"],
                            "embedding": Binary(eval(cluster["embedding"])),
                            "classes": cluster["classes"],
                            "last_time": datetime.fromisoformat(cluster["time"]),
                        },
                        "$addToSet": {"news_ids": cluster["msg_id"]},
                    }
                )
