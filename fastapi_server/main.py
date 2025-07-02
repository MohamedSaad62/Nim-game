from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List

app = FastAPI()
connections: Dict[str, List[WebSocket]] = {}

@app.websocket("/ws/nim/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()

    if game_id not in connections:
        connections[game_id] = []
    connections[game_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            for conn in connections[game_id]:
                if conn != websocket:
                    await conn.send_text(data)  # Broadcast full game state
    except WebSocketDisconnect:
        connections[game_id].remove(websocket)
