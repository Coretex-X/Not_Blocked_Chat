import requests as rq
import websocket
import queue
import json
import threading

sesion = {
    "id_users": 2,
    "token": "ojmdhfjilmanmnibdjodgoomdbohddodclokaedbomjdnceohkiecafgeejogihg%w=L&Qe$_z%y52T&C4ev?eCo]6$W-]URE_K#"
}

response = rq.post("http://127.0.0.1:5000/notification/v2/user/notification/", json=sesion)

try:
    data = response.json()
    print("JSON response:", json.dumps(data, indent=2, ensure_ascii=False))
except:
    print("Response is not JSON")

'''
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