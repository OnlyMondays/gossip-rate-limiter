import os
from fastapi import FastAPI

NODE_ID = os.getenv("NODE_ID", "node_a")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "100"))

app = FastAPI()

@app.get("/status")
async def status():
    return {
        "node_id": NODE_ID,
        "global_total": 0,
        "limit": RATE_LIMIT,
    }