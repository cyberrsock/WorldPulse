from urllib.parse import quote_plus as quote
from typing import Dict, List
import pymongo
import os


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

    def add_news_entry(self,
                       content: str,
                       categories: List[int],
                       database_name: str = "worldpulse",
                       collection_name: str = "news") -> str:
        doc = self.prepare_news_entry(content, categories)

        with self._get_connection() as client:
            db = client[database_name]
            result = db[collection_name].insert_one(doc)
            return str(result.inserted_id)

    def get_all_news(self,
                     database_name: str = "worldpulse",
                     collection_name: str = "news") -> List[Dict]:
        with self._get_connection() as client:
            db = client[database_name]
            collection = db[collection_name]

            return [{
                "_id": doc["_id"],
                "content": doc["content"],
                "categories": doc.get("categories", []),
                "embedding": doc["embedding"]
            } for doc in collection.find()]

    def get_news_dict(self,
                      database_name: str = "worldpulse",
                      collection_name: str = "news") -> Dict[str, Dict]:
        with self._get_connection() as client:
            db = client[database_name]
            collection = db[collection_name]

            news_dict = {}
            for doc in collection.find():
                n_id = str(doc.get("_id"))
                if not n_id:
                    continue
                news_dict[n_id] = {
                    "msg_id": doc.get("msg_id"),
                    "channel": doc.get("channel"),
                    "content": doc.get("content"),
                    "datetime": doc.get("datetime").isoformat() if "datetime" in doc else None,
                }

            return news_dict

    # Получаем всех пользователей из коллекции "users"
    def get_users(self) -> List[Dict]:
        with self._get_connection() as client:
            db = client["worldpulse"]
            collection = db["users"]
            return list(collection.find())

    def get_clusterized_news(self) -> List[Dict]:
        with self._get_connection() as client:
            db = client["worldpulse"]
            collection = db["clusterized_news"]

            # Агрегационный запрос
            pipeline = [
                {
                    "$lookup": {
                        "from": "news",
                        "localField": "news_ids",
                        "foreignField": "_id",
                        "as": "news_items"
                    }
                },
                {
                    "$unwind": "$news_items"
                },
                {
                    "$lookup": {
                        "from": "sources",
                        "localField": "news_items.channel",
                        "foreignField": "name",
                        "as": "source_info"
                    }
                },
                {
                    "$unwind": "$source_info"
                },
                {
                    "$group": {
                        "_id": "$_id",
                        "description": {
                            "$first": "$description"
                        },
                        "classes": {
                            "$first": "$classes"
                        },
                        "first_time": {
                            "$first": "$first_time"
                        },
                        "last_time": {
                            "$first": "$last_time"
                        },
                        "channels": {
                            "$push": {
                                "msg_id": "$news_items.msg_id",  # msg_id
                                "tg_id": "$source_info.attrs.tg_id",  # tg_id
                                "channel_name": "$news_items.channel"  # Название канала
                            }
                        }
                    }
                }
            ]

            results = collection.aggregate(pipeline)

            # Преобразуем результат в нужный формат
            return [
                {
                    "_id": str(doc["_id"]),
                    "description": doc["description"],
                    "classes": doc.get("classes", []),
                    "first_time": doc["first_time"].isoformat(),
                    "last_time": doc["last_time"].isoformat(),
                    "channels": [
                        {
                            "msg_id": channel["msg_id"],
                            "tg_id": channel["tg_id"],
                            "channel_name": channel["channel_name"]
                        }
                        for channel in doc.get("channels", [])
                    ]
                }
                for doc in results
            ]

    def update_user_last_sending(self, user_id, time_str):
        with self._get_connection() as client:
            db = client["worldpulse"]
            db.users.update_one(
                {"_id": user_id},
            {"$set": {"settings.last_sending": time_str}}
            )

    def get_categories(self) -> Dict[str, Dict]:
        """Получаем все категории в формате {category_id: category_data}"""
        with self._get_connection() as client:
            db = client["worldpulse"]
            collection = db["categories"]
            return {
                str(cat["_id"]): {
                    "name": cat["name"],
                    "topic": cat["topic"]
                }
                for cat in collection.find()
            }

    def get_sources(self) -> Dict[str, str]:
        """Получаем все источники в формате {source_id: source_name}"""
        with self._get_connection() as client:
            db = client["worldpulse"]
            collection = db["sources"]  # Предполагаем, что коллекция называется "sources"
            return {
                str(src["_id"]): src["name"]
                for src in collection.find()
            }

