import asyncio
import time

class AsyncRateLimiter:
    def __init__(self, rate: float = 5.0, burst: int = 10):
        if rate <= 0 or burst < 1: raise ValueError("rate and burst must be positive")
        self.rate, self.capacity = rate, float(burst)
        self.tokens = float(burst)
        self.updated = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait)
