import asyncio
import json
import os
import random
import time
from contextlib import asynccontextmanager


import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from gcounter import GCounter

# Config
NODE_ID = os.getenv("NODE_ID", "node_a")
PEERS = [p for p in os.getenv("PEERS", "").split(",") if p]
print(f"NODE_ID: {NODE_ID}")
print(f"PEERS: {PEERS}")
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

# Gossip loop

async def gossip_loop() -> None:
    '''
    Every 200ms, we pick a random peer node, send our counts, and then merge what comes back.

    Important stuff:
    - we have a set 200ms interval which is slow enough not to flood the network but also reasonably fast. each node gets around 5 gossips per second
    - random peer node selection means that over time, every node will eventually be up-to-date
    - if a node fails, no problem, we ball nonetheless
    '''

    while True:
        await asyncio.sleep(0.2)
        if not PEERS:
            continue

        peer = random.choice(PEERS)
        try:
            async with httpx.AsyncClient(timeout=0.5) as client:
                async with mutex_lock:
                    snapshot = counter.snapshot()
                    window = window_start
                
                resp = await client.post(
                    f"{peer}/gossip",
                    json={
                        "counts": snapshot,
                        "window": window,
                    },
                )
                if resp.status_code == 200:
                    payload = resp.json()
                    async with mutex_lock:
                        if payload.get("window") == window_start:
                            counter.merge(payload["counts"])
        except Exception:
            pass # if we reach here, the peer node is offline/down, just ignore and go to the next peer

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(gossip_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

# App

app = FastAPI(lifespan = lifespan)

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
    
@app.post("/gossip")
async def gossip(payload: dict):
    async with mutex_lock:
        await maybe_reset()
        if payload.get("window") == window_start:
            counter.merge(payload["counts"])
        return {
            "counts": counter.snapshot(),
            "window": window_start,
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

@app.get("/events")
async def events():
    '''
    SSE stream for dashboard
    '''
    async def stream():
        while True:
            async with mutex_lock:
                data = {
                    "node_id": NODE_ID,
                    "global_total": counter.total(),
                    "limit": RATE_LIMIT,
                    "counts": counter.snapshot(),
                    **stats,
                }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    
    return StreamingResponse(stream(), media_type = "text/event-stream")