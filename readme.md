# Microservices Basics

### Usage

```commandline
python3 -m venv venv 
source env/bin/activate
pip install -r requirements.txt
```
run in different terminal

```commandline
uvicorn logging_service:app --port 8001
uvicorn logging_service:app --port 8002
uvicorn logging_service:app --port 8003

uvicorn messages_service:app --port 8004
uvicorn messages_service:app --port 8005

uvicorn facade_service:app --port 8000
```

### Photos of logs and send requests
![img_6.png](photos/img_6.png)

![img_1.png](photos/img_1.png)

![img_2.png](photos/img_2.png)

![img_3.png](photos/img_3.png)

![img_4.png](photos/img_4.png)

![img_5.png](photos/img_5.png)

![img.png](photos/img.png)

![img_7.png](photos/img_7.png)