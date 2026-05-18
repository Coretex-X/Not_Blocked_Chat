import requests as rq
import websocket
import queue
import json
import threading


json_login = {
    "login":"User1",
    "password":"12345678"
}
response_login = rq.post("http://127.0.0.1:5000/api/v2/user/login/", json=json_login)
data = response_login.json()
print(data)

'''json_reqistartion = {
    "login":"User2",
    "email":"user2@mail.ru",
    "number":"9999999992",
    "password":"12345678"
}
response = rq.post("http://127.0.0.1:5000/api/v2/user/registration/", json=json_reqistartion)
print(response)'''

'''sesion = {
    "id_users": 2,
    "token": "opjejcaggmlhjhkadodpfpkiihbbgbcogdgncmilfnpadnampoefaokkbpibjgni7Z&>$~IvI-O+t%'gz#<pFfSH?ICZ`*E1XOkT"
}

response = rq.post("http://127.0.0.1:5000/notification/v2/user/notification/", json=sesion)

try:
    data = response.json()
    print("JSON response:", json.dumps(data, indent=2, ensure_ascii=False))
except:
    print("Response is not JSON")


# 1. Аутентификация
ws_auth = websocket.WebSocket()
ws_auth.connect("ws://127.0.0.1:5000/ws/data/")
ws_auth.send(json.dumps({
    "room": "lobbi",
    "user_id": 1,
    "guest_id": 2,
    "status_chat": "existing_chat",
    "token": "api87"
}))#existing_chat


# Создаем очередь для сообщений
message_queue = queue.Queue()
ws_auth.close()

# 2. Подключаемся к чату
ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:5000/ws/chat_user/api87/")

def receive_messages():
    while True:
        try:
            message = ws.recv()
            print(f"\nReceived: {message}")
            # КЛАДЕМ сообщение в очередь вместо прямого вывода
            message_queue.put(message)
        except Exception as e:
            print(f"\nDisconnected: {e}")
            break

# Запускаем поток для прослушивания
thread = threading.Thread(target=receive_messages, daemon=True)
thread.start()

# 3. Основной цикл обработки
while True:
    try:
        received_msg = message_queue.get_nowait()
        received_msg_dict = json.loads(received_msg)
    except queue.Empty:
        pass
    message = input()
    ws.send(json.dumps({"message": message}))



#ws.close()'''