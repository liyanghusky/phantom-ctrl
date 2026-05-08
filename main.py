import asyncio
import io
import pathlib
import socket
import subprocess
import sys
from contextlib import asynccontextmanager

import qrcode

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import settings
from auth import require_auth, verify_token
from screen import capture_loop
from ws_manager import manager
from input_handler import handle_click, handle_type, handle_key

BASE_DIR = pathlib.Path(__file__).parent


_capture_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _capture_task
    _capture_task = asyncio.create_task(capture_loop())

    ip = socket.gethostbyname(socket.gethostname())
    token = settings.SECRET_TOKEN
    url = f"http://{ip}:8000/?token={token}"
    sep = "=" * 50
    print(sep)
    print(f"  Token : {token}")
    print(f"  URL   : {url}")
    print()
    qr = qrcode.QRCode()
    qr.add_data(url)
    qr.make()
    buf = io.StringIO()
    qr.print_ascii(invert=True, out=buf)
    sys.stdout.buffer.write(buf.getvalue().encode("utf-8"))
    sys.stdout.buffer.flush()
    print(sep)

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
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ---------- WebSocket ----------

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
        await handle_click(payload.x, payload.y, payload.button)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/type", dependencies=[Depends(require_auth)])
async def api_type(payload: TypePayload):
    try:
        await handle_type(payload.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/key", dependencies=[Depends(require_auth)])
async def api_key(payload: KeyPayload):
    try:
        await handle_key(payload.key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.post("/api/launch", dependencies=[Depends(require_auth)])
async def api_launch():
    try:
        game_path = pathlib.Path(settings.GAME_EXE)
        subprocess.Popen([str(game_path)], cwd=str(game_path.parent))
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Game executable not found.")
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}


@app.get("/api/status", dependencies=[Depends(require_auth)])
async def api_status():
    return {
        "streaming": _capture_task is not None and not _capture_task.done(),
        "connected_clients": len(manager._clients),
        "fps": settings.CAPTURE_FPS,
    }


@app.get("/")
async def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
