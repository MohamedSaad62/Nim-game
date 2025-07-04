from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from typing import Dict, List
import json
import asyncio

app = FastAPI()

# Gameplay connections and state
connections: Dict[str, List[WebSocket]] = {}
game_states: Dict[str, Dict] = {}

# Lobby connections: one websocket per user
lobby_connections: Dict[str, WebSocket] = {}

@app.websocket("/ws/nim/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()

    if game_id not in connections:
        connections[game_id] = []
    connections[game_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "move":
                game_states[game_id] = {
                    "piles": message["piles"],
                    "turn": message["turn"],
                    "last_move_by": message["username"]
                }

                if all(len(pile) == 0 for pile in message["piles"]):
                    game_over = {
                        "type": "game_over",
                        "winner": message["username"]
                    }
                    for conn in connections[game_id]:
                        await conn.send_text(json.dumps(game_over))
                        await conn.close()

                    del connections[game_id]
                    del game_states[game_id]
                    break

                for conn in connections[game_id]:
                    await conn.send_text(json.dumps({
                        "type": "move",
                        "piles": message["piles"],
                        "turn": message["turn"],
                        "username": message["username"]
                    }))

    except WebSocketDisconnect:
        if game_id in connections and websocket in connections[game_id]:
            connections[game_id].remove(websocket)

@app.websocket("/ws/lobby/{username}")
async def lobby_ws(websocket: WebSocket, username: str):
    print("Connected:", username)
    await websocket.accept()
    lobby_connections[username] = websocket

    try:
        while True:
            # Just receive any message to keep connection alive; can ignore content
            await websocket.receive_text()
    except WebSocketDisconnect:
        lobby_connections.pop(username, None)

async def send_lobby_update(to_usernames: List[str], data: dict):
    print("Sending message:", data, "to:", to_usernames)
    message = json.dumps(data)
    for user in to_usernames:
        ws = lobby_connections.get(user)
        if ws:
            try:
                await ws.send_text(message)
            except Exception:
                pass  # Ignore failures silently

@app.post("/notify-lobby/")
async def notify_lobby(request: Request):
    print("Connected users:", list(lobby_connections.keys()))
    data = await request.json()
    to_users = data.get('to_users', [])
    message = data.get('message', {})
    await send_lobby_update(to_users, message)
    return {"status": "ok"}
