"""Worker connections."""

import os
import redis

from rq import Worker, Queue, Connection

from iex.util import constants

listen = ["high", "default", "low"]

if constants.remote_path == r"/app/files/":
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
else:
    # if debugging locally will need a redis
    redis_url = os.getenv("LOCAL_REDIS")

conn = redis.from_url(redis_url)

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()
