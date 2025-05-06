import random
import consul
import os
import atexit
import hazelcast
import requests
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

consul_client = consul.Consul()

app = FastAPI(
    title="Facade Service API",
    description="Фасадний сервіс, що балансує запити між кількома logging-service та messages_service.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "localhost")
INSTANCE_ID = os.getenv("INSTANCE_ID", str(uuid.uuid4()))
service_id = f"facade-service-{INSTANCE_ID}"
check = consul.Check.http(f"http://{HOST}:{PORT}/health", "10s")
consul_client.agent.service.register(
    name="facade-service",
    service_id=service_id,
    address=HOST, port=PORT,
    check=check
)

_, kv = consul_client.kv.get("mq/queue_lab5")
queue_name = kv["Value"].decode() if kv else "msg-queue"
hz_client = hazelcast.HazelcastClient()
queue     = hz_client.get_queue(queue_name).blocking()

class Message(BaseModel):
    message: str

@app.get("/health")
def health(): return {"status": "UP"}

def discover(service_name: str):
    _, nodes = consul_client.health.service(service_name, passing=True)
    return [
        f"http://{n['Service']['Address']}:{n['Service']['Port']}"
        for n in nodes
    ]

@app.post("/messages")
def post_message(msg: Message):
    addrs = discover("logging-service")
    if not addrs:
        raise HTTPException(503, "No logging-service available")
    url = random.choice(addrs) + "/messages"
    resp = requests.post(url, json=msg.dict(), timeout=2)
    if resp.status_code != 200:
        raise HTTPException(502, "Logging-service error")

    queue.put(msg.message)
    print(f"[Facade] Enqueued: {msg.message}")
    return {"status": "queued_and_logged"}

@app.get("/messages")
def get_messages():
    log_addrs = discover("logging-service")
    idx = random.randrange(len(log_addrs))
    if not log_addrs:
        raise HTTPException(503, "No logging-service available")
    for i in range(len(log_addrs)):
        url = log_addrs[(idx + i) % len(log_addrs)] + '/messages'
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                log_msgs = r.json().get("messages", [])
                print(f"[Facade] GET logs from {url}")
                break
        except:
            continue
    else:
        raise HTTPException(503, "Logging-service недоступні")

    msg_addrs = discover("messages-service")
    idx = random.randrange(len(msg_addrs))
    if not msg_addrs:
        raise HTTPException(503, "No messages-service available")
    mq_msgs = []
    for i in range(len(msg_addrs)):
        url = msg_addrs[(idx + i) % len(msg_addrs)] + "/messages"
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                mq_msgs = r.json().get("messages", [])
                print(f"[Facade] GET mq from {url}")
                break
        except:
            continue
    else:
        raise HTTPException(503, "Messages-service недоступні")

    return {"messages_from_logging": log_msgs, "messages_from_messaging": mq_msgs}

@atexit.register
def deregister():
    consul_client.agent.service.deregister(service_id)
