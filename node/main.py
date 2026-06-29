import asyncio
import os
import time

import httpx
from fastapi import FastAPI

from gcounter import GCounter

# Config
NODE_ID = os.getenv("NODE_ID", "node_a")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))
RIFTCODEX = os.getenv("RIFTCODEX_URL", "https://api.riftcodex.com")

# State
counter = GCounter(NODE_ID)
window_start = int(time.time() // 60)
stats = {"allowed": 0, "rejected": 0, "riftcodex_hits": 0}
mutex_lock = asyncio.Lock()

# Helpers
def current_window() -> int:
    return int(time.time() // 60)

async def maybe_reset() -> None:
    '''Reset counter if a new minute has started, ONLY call with mutex_lock held.'''
    global counter, window_start, stats
    if current_window() != window_start:
        counter.reset()
        window_start = current_window()
        stats = {"allowed": 0, "rejected": 0, "riftcodex_hits": 0}

# App

app = FastAPI()

@app.post("/request")
async def handle_request(body: dict):
    async with mutex_lock:
        await maybe_reset()

        if counter.total() >= RATE_LIMIT:
            stats["rejected"] += 1
            return {
                "allowed": False,
                "reason": "rate_limit_exceeded",
                "global_total": counter.total(),
                "limit": RATE_LIMIT,
            }
        
        counter.increment()
        stats["allowed"] += 1
    
    query = body.get("query", "")
    try:
        async with httpx.AsyncClient(timeout = 5.0) as client:
            response = await client.get(
                f"{RIFTCODEX}/cards",
                params = {"search": query},
            )
        
        async with mutex_lock:
            stats["riftcodex_hits"] += 1
        
        return {
            "allowed": True,
            "data": response.json(),
            "global_total": counter.total(),
        }
    
    except Exception as e:
        return {
            "allowed": True,
            "error": str(e),
            "global_total": counter.total(),
        }
        

@app.get("/status")
async def status():
    async with mutex_lock:
        await maybe_reset()
        return {
            "node_id": NODE_ID,
            "global_total": counter.total(),
            "limit": RATE_LIMIT,
            "window": window_start,
            "counts": counter.snapshot(),
            **stats,
        }