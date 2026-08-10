import asyncio
import json
import os

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

NODES = [n for n in os.getenv("NODES", "").split(",") if n]

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


async def poll_all() -> dict:
    async with httpx.AsyncClient(timeout=1.0) as client:
        tasks     = [client.get(f"{node}/status") for node in NODES]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    nodes_data: list     = []
    merged_counts: dict  = {}
    total_allowed        = 0
    total_rejected       = 0
    total_api_hits = 0
    limit                = 100

    for node_url, resp in zip(NODES, responses):
        if isinstance(resp, Exception):
            nodes_data.append({"node_url": node_url, "offline": True})
            continue

        data             = resp.json()
        data["node_url"] = node_url
        nodes_data.append(data)

        for node_id, count in data.get("counts", {}).items():
            merged_counts[node_id] = max(merged_counts.get(node_id, 0), count)

        total_allowed        += data.get("allowed", 0)
        total_rejected       += data.get("rejected", 0)
        total_api_hits += data.get("api_hits", 0)
        limit                 = data.get("limit", 100)

    return {
        "nodes":          nodes_data,
        "global_total":   sum(merged_counts.values()),
        "merged_counts":  merged_counts,
        "limit":          limit,
        "total_allowed":  total_allowed,
        "total_rejected": total_rejected,
        "total_hits":     total_api_hits,
        "online_count":   sum(1 for n in nodes_data if not n.get("offline")),
        "node_count":     len(NODES),
    }


@app.get("/")
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.get("/aggregate")
async def aggregate():
    return await poll_all()


@app.get("/stream")
async def stream():
    async def generate():
        while True:
            data = await poll_all()
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(generate(), media_type="text/event-stream")