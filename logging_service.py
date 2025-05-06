import os
import subprocess
import time
import atexit
import uuid

import hazelcast
import consul

from fastapi import FastAPI
from pydantic import BaseModel

consul_client = consul.Consul()
_, kv = consul_client.kv.get("hazelcast/lab5")
cluster_name = kv["Value"].decode() if kv else "dev"

hz_proc = subprocess.Popen(["hz", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def _stop_hz():
    hz_proc.terminate()
    hz_proc.wait(5)
atexit.register(_stop_hz)
time.sleep(5)

client = hazelcast.HazelcastClient(cluster_name=cluster_name)
messages_map = client.get_map("logging-messages").blocking()

app = FastAPI()
PORT = int(os.getenv("PORT", 8001))
HOST = os.getenv("HOST", "localhost")


INSTANCE_ID = os.getenv("INSTANCE_ID", str(uuid.uuid4()))
service_id = f"logging-service-{INSTANCE_ID}"

check = consul.Check.http(f"http://{HOST}:{PORT}/health", "10s")
consul_client.agent.service.register(
    name="logging-service",
    service_id=service_id,
    address=HOST, port=PORT,
    check=check
)


class Message(BaseModel):
    message: str

@app.get("/health")
def health(): return {"status": "UP"}

@app.post("/messages")
def save_message(msg: Message):
    msg_id = str(uuid.uuid4())
    messages_map.put(msg_id, msg.message)
    print(f"[Instance {INSTANCE_ID}] Saved message {msg_id}: '{msg.message}'")
    return {
        "instance": INSTANCE_ID,
        "message_id": msg_id,
        "status": "saved",
    }

@app.get("/messages")
def get_all_messages():
    all_entries = messages_map.entry_set()
    result = {k: v for k, v in all_entries}
    print(f"[Instance {INSTANCE_ID}] Returning {len(result)} messages")
    return {"messages": result}

# @atexit.register
# def deregister():
  #  consul_client.agent.service.deregister(service_id)
