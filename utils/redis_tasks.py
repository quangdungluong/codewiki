import json

import redis


class RedisTasks:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_client = redis.Redis(host=host, port=port, db=db)

    def add_task(self, task_id: str, task_data: dict):
        self.redis_client.set(task_id, json.dumps(task_data))

    def get_task(self, task_id: str) -> dict:
        data = self.redis_client.get(task_id)
        if data is None:
            return None
        return json.loads(data)

    def update_task(self, task_id: str, task_data: dict):
        task = self.get_task(task_id)
        if task is None:
            return
        task.update(task_data)
        self.redis_client.set(task_id, json.dumps(task))

    def delete_task(self, task_id: str):
        self.redis_client.delete(task_id)

    def get_all_tasks(self) -> list[dict]:
        return [
            json.loads(self.redis_client.get(task_id))
            for task_id in self.redis_client.keys()
        ]
