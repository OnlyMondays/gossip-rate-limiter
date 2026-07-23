import asyncio
import os
import random
import time

import httpx

NODES = [n for n in os.getenv("NODES", "").split(",") if n]
RPM   = int(os.getenv("REQUESTS_PER_MINUTE", "200"))

QUERIES = [
    "dragon", "sentinel", "void", "archer",
    "rift",  "ancient", "mage", "frost",
    "knight", "tide", "bone", "sky",
]

stats = {
    "sent":          0,
    "allowed":       0,
    "rejected":      0,
    "errors":        0,
    "window_allowed": 0,
    "window_start":  time.time(),
}


async def fire(client: httpx.AsyncClient) -> None:
    node  = random.choice(NODES)
    query = random.choice(QUERIES)
    try:
        resp = await client.post(
            f"{node}/request",
            json={"query": query},
            timeout=2.0,
        )
        data = resp.json()
        stats["sent"] += 1
        if data.get("allowed"):
            stats["allowed"] += 1
            stats["window_allowed"] += 1
        else:
            stats["rejected"] += 1
    except Exception:
        stats["errors"] += 1
        stats["sent"] += 1


async def report() -> None:
    while True:
        await asyncio.sleep(10)

        # Per-window rate (resets each minute)
        window_elapsed = time.time() - stats["window_start"]
        window_rpm     = (stats["window_allowed"] / window_elapsed) * 60 if window_elapsed > 0 else 0
        reject_pct     = (stats["rejected"] / stats["sent"] * 100) if stats["sent"] > 0 else 0

        # Reset window if a new minute has started
        if window_elapsed >= 60:
            stats["window_allowed"] = 0
            stats["window_start"]   = time.time()

        print(
            f"[{time.strftime('%H:%M:%S')}]  "
            f"sent={stats['sent']}  "
            f"allowed={stats['allowed']}  "
            f"rejected={stats['rejected']}  "
            f"errors={stats['errors']}  "
            f"window_rate={window_rpm:.1f}/min  "
            f"reject_pct={reject_pct:.1f}%"
        )


async def main() -> None:
    if not NODES:
        print("ERROR: NODES environment variable not set.")
        print("Example: $env:NODES = 'http://localhost:8001,http://localhost:8002'")
        return

    interval = 60 / RPM
    print(f"Targeting {RPM} req/min across {len(NODES)} nodes")
    print(f"Interval between requests: {interval:.3f}s")
    print(f"Expected: ~100 allowed/min, ~{RPM - 100} rejected/min\n")

    asyncio.create_task(report())

    async with httpx.AsyncClient() as client:
        while True:
            asyncio.create_task(fire(client))
            await asyncio.sleep(interval)


asyncio.run(main())