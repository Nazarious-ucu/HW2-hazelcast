import os
import subprocess
import time
import atexit
import uuid

import hazelcast
from fastapi import FastAPI
from pydantic import BaseModel

# ─── Запускаємо Hazelcast‑нод через ваш CLI (припустимо, 'hz start' працює) ────
hz_proc = subprocess.Popen(["hz", "start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def _stop_hz():
    # просто вбиваємо процес ноди
    hz_proc.terminate()
    hz_proc.wait(timeout=5)

atexit.register(_stop_hz)

# даємо ноді час приєднатись до кластеру
time.sleep(5)

# ─── Підключаємо клієнта до кластеру та беремо розподілену мапу ───────────────
client = hazelcast.HazelcastClient()
messages_map = client.get_map("messages").blocking()

app = FastAPI()
INSTANCE_ID = os.environ.get("INSTANCE_ID", "unknown")

class Message(BaseModel):
    message: str

@app.post("/messages")
def save_message(msg: Message):
    # генеруємо унікальний ключ самі
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
    # повертаємо dict id→text
    all_entries = messages_map.entry_set()  # List of (key, value)
    result = {k: v for k, v in all_entries}
    print(f"[Instance {INSTANCE_ID}] Returning {len(result)} messages")
    return {"messages": result}
