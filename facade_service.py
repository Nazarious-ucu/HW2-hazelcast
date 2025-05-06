import random
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="Facade Service API",
    description="Фасадний сервіс, що балансує запити між кількома logging-service та реалізує fallback.",
    version="1.0.0",
    docs_url="/docs",         # Swagger UI
    redoc_url="/redoc",       # ReDoc
    openapi_url="/openapi.json"
)

# Список URL-адрес доступних екземплярів logging-service
logging_services = [
    "http://localhost:8001/messages",
    "http://localhost:8002/messages",
    "http://localhost:8003/messages",
]

class Message(BaseModel):
    message: str

class MessageResponse(BaseModel):
    instance: str
    message_id: str
    status: str

class MessagesResponse(BaseModel):
    messages: dict[str, str]

@app.post(
    "/messages",
    response_model=MessageResponse,
    summary="Зберегти повідомлення",
    description="Приймає JSON з полем `message` та записує його до одного з logging-service через HTTP POST.",
    tags=["Messages"]
)
def post_message(msg: Message):
    start_index = random.randrange(len(logging_services))
    for i in range(len(logging_services)):
        url = logging_services[(start_index + i) % len(logging_services)]
        try:
            resp = requests.post(url, json=msg.dict(), timeout=2)
        except Exception:
            print(f"[Facade] {url} недоступний, спроба #{i+1}")
            continue
        if resp.status_code == 200:
            data = resp.json()
            print(f"[Facade] POST → {url} OK: {data}")
            return data
        else:
            print(f"[Facade] {url} повернув {resp.status_code}")
    raise HTTPException(status_code=503, detail="No logging-service available")

@app.get(
    "/messages",
    response_model=MessagesResponse,
    summary="Отримати всі повідомлення",
    description="Повертає всі повідомлення, які є у розподіленій мапі Hazelcast через будь‑який доступний logging-service.",
    tags=["Messages"]
)
def get_messages():
    start_index = random.randrange(len(logging_services))
    for i in range(len(logging_services)):
        url = logging_services[(start_index + i) % len(logging_services)]
        try:
            resp = requests.get(url, timeout=2)
        except Exception:
            print(f"[Facade] {url} недоступний, спроба #{i+1}")
            continue
        if resp.status_code == 200:
            data = resp.json()
            print(f"[Facade] GET → {url} returned {len(data.get('messages', {}))} msgs")
            return data
        else:
            print(f"[Facade] {url} повернув {resp.status_code}")
    raise HTTPException(status_code=503, detail="No logging-service available")
