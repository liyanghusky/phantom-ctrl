import asyncio
import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings
from auth import require_auth
from screen import capture_loop
from ws_manager import manager
from input_handler import handle_click, handle_type, handle_key


_capture_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _capture_task
    _capture_task = asyncio.create_task(capture_loop())
    yield
    if _capture_task:
        _capture_task.cancel()
        try:
            await _capture_task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------- WebSocket ----------

def verify_token(token: str) -> bool:
    return token == settings.SECRET_TOKEN


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket, token: str = ""):
    if not verify_token(token):
        await ws.close(code=4001)
        return
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------- Input models ----------

class ClickPayload(BaseModel):
    x: float
    y: float
    button: str = "left"


class TypePayload(BaseModel):
    text: str


class KeyPayload(BaseModel):
    key: str


# ---------- API routes ----------

@app.post("/api/click", dependencies=[Depends(require_auth)])
async def api_click(payload: ClickPayload):
    try:
        handle_click(payload.x, payload.y, payload.button)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/type", dependencies=[Depends(require_auth)])
async def api_type(payload: TypePayload):
    try:
        handle_type(payload.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/key", dependencies=[Depends(require_auth)])
async def api_key(payload: KeyPayload):
    try:
        handle_key(payload.key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/launch", dependencies=[Depends(require_auth)])
async def api_launch():
    try:
        subprocess.Popen([settings.GAME_EXE])
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Game executable not found.")
    except OSError:
        pass
    return {"ok": True}


@app.get("/api/status", dependencies=[Depends(require_auth)])
async def api_status():
    return {
        "streaming": _capture_task is not None and not _capture_task.done(),
        "connected_clients": len(manager.active_connections),
        "fps": settings.CAPTURE_FPS,
    }


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
