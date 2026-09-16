import json
import os
import time
from typing import Any

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE = os.getenv("REDIS_QUEUE", "socialintel:jobs")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def process(job: dict[str, Any]) -> None:
    kind = job.get("kind")
    if kind == "noop":
        return
    raise ValueError(f"Unsupported job kind: {kind}")


def main() -> None:
    while True:
        item = r.brpop(QUEUE, timeout=5)
        if not item:
            continue
        _, payload = item
        try:
            process(json.loads(payload))
        except Exception as exc:
            print(f"job failed: {type(exc).__name__}", flush=True)


if __name__ == "__main__":
    main()
