import os
import threading
import time

import hazelcast
from fastapi import FastAPI

app = FastAPI()
INSTANCE_ID = os.environ.get("INSTANCE_ID", "unknown")

client = hazelcast.HazelcastClient()
queue  = client.get_queue("msg-queue").blocking()

stored = []

def consume_loop():
    while True:
        msg = queue.take()
        stored.append(msg)
        print(f"[MsgSvc {INSTANCE_ID}] Consumed: {msg}")

@app.on_event("startup")
def startup():
    t = threading.Thread(target=consume_loop, daemon=True)
    t.start()

@app.get("/messages")
def get_messages():
    print(f"[MsgSvc {INSTANCE_ID}] Returning {len(stored)} messages")
    return {"instance": INSTANCE_ID, "messages": stored}
