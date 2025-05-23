from fastapi import FastAPI, WebSocket
from datetime import datetime
import socketio
import os
import jwt
from dotenv import load_dotenv
import uvicorn
load_dotenv()

app = FastAPI()


JWT_SECRET = os.getenv("JWT_SECRET")


sio_server = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
sio_app = socketio.ASGIApp(sio_server)

user_socket_map = {}
messages = []

app.mount("/", sio_app)


@app.get('/')
async def root():
    return {"data": "HELLO WORLD"}


@sio_server.event
async def connect(sid, environ, auth):
    user_id = auth.get("userId")
    print(f"User ID: {user_id}")

    # if not token:
    #     print("No token in cookie")
    #     return False

    # try:
    #     payload = jwt.decode(token, "secret", algorithms=["HS256"])
    #     user_id = payload["user_id"]
    #     user_socket_map[user_id] = sid
    #     print(f"User {user_id} connected")
    # except jwt.InvalidTokenError:
    #     print("Invalid token in cookie")
    #     return False

    user_socket_map[user_id] = sid
    print(f"User {user_id} connected with sid {sid}")


@sio_server.event
async def disconnect(sid):
    for user_id, stored_sid in list(user_socket_map.items()):
        if stored_sid == sid:
            del user_socket_map[user_id]
            print(f"User {user_id} disconnected")
            break


@sio_server.event
async def private_message(sid, data):
    to = data.get("to")
    message = data.get("message")

    print(f"Received private message from {sid} to {to}: {message}")
    from_user = None

    # Find who sent the message based on their sid
    for user_id, stored_sid in user_socket_map.items():
        if stored_sid == sid:
            from_user = user_id
            break

    if not from_user:
        print("Sender not recognized")
        return

    print(f"[Private] {from_user} ➡ {to}: {message}")

    recipient_sid = user_socket_map.get(to)

    if recipient_sid:
        await sio_server.emit("private-message", {
            "from": from_user,
            "message": message,
            "time": datetime.now()
        }, to=recipient_sid)


# Run server with `python main.py`
if __name__ == "__main__":
    print("🚀 Starting Interviewer WebSocket Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
