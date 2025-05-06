import os
import threading
import atexit, uuid
import consul
import hazelcast
from fastapi import FastAPI

consul_client = consul.Consul()
app = FastAPI()

PORT = int(os.getenv("PORT", 8004))
HOST = os.getenv("HOST", "localhost")

INSTANCE_ID = os.getenv("INSTANCE_ID", str(uuid.uuid4()))
service_id = f"messages-service-{INSTANCE_ID}"

check = consul.Check.http(f"http://{HOST}:{PORT}/health", "10s")
consul_client.agent.service.register(
    name="messages-service",
    service_id=service_id,
    address=HOST, port=PORT,
    check=check
)

_, kv = consul_client.kv.get("mq/queue_lab5")
queue_name = kv["Value"].decode() if kv else "msg-queue"

client = hazelcast.HazelcastClient()
queue  = client.get_queue(queue_name).blocking()

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

@app.get("/health")
def health(): return {"status": "UP"}

@app.get("/messages")
def get_messages():
    print(f"[MsgSvc {INSTANCE_ID}] Returning {len(stored)} messages")
    return {"instance": INSTANCE_ID, "messages": stored}

@atexit.register
def deregister():
    consul_client.agent.service.deregister(service_id)
