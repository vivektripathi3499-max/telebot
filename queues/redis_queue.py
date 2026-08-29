import asyncio
import json
import os

import redis.asyncio as redis
from redis.exceptions import TimeoutError as RedisTimeoutError


REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://127.0.0.1:6379/0",
)


class RedisQueue:
    def __init__(self, name: str):
        self.name = name

        self.client = redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=None,
            health_check_interval=30,
        )

    async def put(self, data: dict) -> None:
        await self.client.rpush(
            self.name,
            json.dumps(data),
        )

    async def get(self, timeout: int = 5):
        """
        Wait for an item.

        A timeout simply means the queue was empty.
        It must NOT terminate the worker.
        """

        while True:
            try:
                result = await self.client.blpop(
                    self.name,
                    timeout=timeout,
                )

                if result is None:
                    return None

                _, payload = result

                return json.loads(payload)

            except RedisTimeoutError:
                # Redis socket timeout should not kill the worker.
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                raise

    async def close(self) -> None:
        await self.client.aclose()

