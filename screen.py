import asyncio
import io

import mss
from PIL import Image

from config import settings
from ws_manager import manager


def _capture_jpeg() -> bytes:
    with mss.mss() as sct:
        if settings.SCREEN_INDEX >= len(sct.monitors):
            raise RuntimeError(f"SCREEN_INDEX {settings.SCREEN_INDEX} out of range ({len(sct.monitors)} monitors found)")
        monitor = sct.monitors[settings.SCREEN_INDEX]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    img = img.resize((1280, 720), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=settings.JPEG_QUALITY)
    return buf.getvalue()


async def capture_loop():
    interval = 1 / settings.CAPTURE_FPS
    while True:
        try:
            jpeg_bytes = await asyncio.to_thread(_capture_jpeg)
            await manager.broadcast(jpeg_bytes)
        except Exception as e:
            print(f"[capture_loop] error: {e}")
        await asyncio.sleep(interval)
