import asyncio
import re
import pyautogui
import pyperclip

pyautogui.FAILSAFE = True

_screen_w, _screen_h = pyautogui.size()

ALLOWED_BUTTONS = {"left", "right"}
ALLOWED_KEYS = {"enter", "tab", "escape", "backspace", "space", "up", "down", "left", "right"}


def _click(x_ratio: float, y_ratio: float, button: str) -> None:
    if not (0.0 <= x_ratio <= 1.0 and 0.0 <= y_ratio <= 1.0):
        raise ValueError(f"Coordinates must be in [0, 1], got ({x_ratio}, {y_ratio})")
    if button not in ALLOWED_BUTTONS:
        raise ValueError(f"button must be 'left' or 'right', got '{button}'")
    x = int(x_ratio * _screen_w)
    y = int(y_ratio * _screen_h)
    pyautogui.click(x, y, button=button)


def _type(text: str) -> None:
    if len(text) > 256:
        raise ValueError(f"text length must be <= 256, got {len(text)}")
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    if text.isascii():
        pyautogui.typewrite(text, interval=0.02)
    else:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")


def _key(key: str) -> None:
    if key not in ALLOWED_KEYS:
        raise ValueError(f"key '{key}' is not allowed; allowed: {ALLOWED_KEYS}")
    pyautogui.press(key)


async def handle_click(x_ratio: float, y_ratio: float, button: str = "left") -> None:
    await asyncio.to_thread(_click, x_ratio, y_ratio, button)


async def handle_type(text: str) -> None:
    await asyncio.to_thread(_type, text)


async def handle_key(key: str) -> None:
    await asyncio.to_thread(_key, key)
