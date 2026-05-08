import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    SECRET_TOKEN: str = os.getenv("SECRET_TOKEN", "")
    CAPTURE_FPS: int = int(os.getenv("CAPTURE_FPS", "10"))
    JPEG_QUALITY: int = int(os.getenv("JPEG_QUALITY", "60"))
    SCREEN_INDEX: int = int(os.getenv("SCREEN_INDEX", "0"))
    GAME_EXE: str = os.getenv("GAME_EXE", "")


settings = Settings()

if not settings.SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN must be set in .env")
