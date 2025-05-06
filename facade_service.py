# facade_service.py
import random

import hazelcast
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Facade Service API",
    description="Фасадний сервіс, що балансує запити між кількома logging-service та messages_service.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

logging_services = [
    "http://localhost:8001/messages",
    "http://localhost:8002/messages",
    "http://localhost:8003/messages",
]
messages_services = [
    "http://localhost:8004/messages",
    "http://localhost:8005/messages",
]


hz = hazelcast.HazelcastClient()
queue = hz.get_queue("msg-queue").blocking()

class Message(BaseModel):
    message: str

@app.post("/messages")
def post_message(msg: Message):
    idx = random.randrange(len(logging_services))
    for i in range(len(logging_services)):
        url = logging_services[(idx + i) % len(logging_services)]
        try:
            r = requests.post(url, json=msg.dict(), timeout=2)
            if r.status_code == 200:
                print(f"[Facade] POST ⇒ {url} OK")
                break
        except:
            continue
    else:
        raise HTTPException(503, "Logging-service недоступні")
    queue.put(msg.message)
    print(f"[Facade] Enqueued: {msg.message}")
    return {"status": "queued_and_logged"}

@app.get("/messages")
def get_messages():
    idx = random.randrange(len(logging_services))
    log_msgs = []
    for i in range(len(logging_services)):
        url = logging_services[(idx + i) % len(logging_services)]
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

    idx = random.randrange(len(messages_services))
    mq_msgs = []
    for i in range(len(messages_services)):
        url = messages_services[(idx + i) % len(messages_services)]
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
