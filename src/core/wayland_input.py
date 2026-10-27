"""
Wayland input and screen capture for Hyprland (Omarchy), replacing PyAutoGUI.

PyAutoGUI only sees XWayland windows, so on a Wayland desktop it cannot
screenshot or control normal apps. This backend uses the compositor's tools:

- screenshots: grim (whole screen or a region)
- cursor moves: hyprctl dispatch (Lua form on Hyprland 0.55+, legacy movecursor before)
- typing and keys: wtype (Wayland virtual keyboard)
- clicks, scrolling, dragging: ydotool (needs the ydotoold daemon; it writes
  to /dev/uinput, so the user needs access to it)

Selection: GROKPUTER_INPUT_BACKEND=wayland|pyautogui|auto (default auto).
auto picks wayland when WAYLAND_DISPLAY is set and grim is installed.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image

ENV_VAR = "GROKPUTER_INPUT_BACKEND"

# PyAutoGUI key names -> xkb keysym names understood by wtype
KEY_NAMES = {
    "enter": "Return", "return": "Return", "esc": "Escape", "escape": "Escape",
    "tab": "Tab", "backspace": "BackSpace", "delete": "Delete", "del": "Delete",
    "space": "space", "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "home": "Home", "end": "End", "pageup": "Prior", "pagedown": "Next",
    "insert": "Insert", "capslock": "Caps_Lock", "printscreen": "Print",
}
MODIFIERS = {
    "ctrl": "ctrl", "control": "ctrl", "shift": "shift", "alt": "alt",
    "win": "logo", "super": "logo", "command": "logo", "cmd": "logo", "meta": "logo",
}
# ydotool click codes: 0x00 left, 0x01 right, 0x02 middle; +0x40 press, +0x80 release
BUTTONS = {"left": 0x00, "right": 0x01, "middle": 0x02}
PRESS, RELEASE = 0x40, 0x80


class WaylandInputUnavailable(RuntimeError):
    """A required Wayland tool is missing."""


def backend_name(env: Optional[Dict[str, str]] = None) -> str:
    """Return "wayland" or "pyautogui" for this session."""
    env = os.environ if env is None else env
    choice = env.get(ENV_VAR, "auto").strip().lower()
    if choice in ("wayland", "pyautogui"):
        return choice
    if env.get("WAYLAND_DISPLAY") and shutil.which("grim"):
        return "wayland"
    return "pyautogui"


def wtype_key_name(key: str) -> str:
    lowered = key.lower()
    if lowered in KEY_NAMES:
        return KEY_NAMES[lowered]
    if len(lowered) in (2, 3) and lowered[0] == "f" and lowered[1:].isdigit():
        return key.upper()
    return key


class WaylandInput:
    """Runs the Wayland tools. `run` and `which` are injectable for tests."""

    def __init__(self, run=None, which=shutil.which):
        self._run = run or self._run_subprocess
        self._which = which

    @staticmethod
    def _run_subprocess(argv: Sequence[str]) -> bytes:
        result = subprocess.run(list(argv), capture_output=True, timeout=15, check=False)
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip() or f"exit {result.returncode}"
            raise RuntimeError(f"{argv[0]} failed: {message}")
        return result.stdout

    def _need(self, tool: str, hint: str) -> None:
        if not self._which(tool):
            raise WaylandInputUnavailable(f"{tool} is not installed: {hint}")

    def _ydotool(self, *args: str) -> None:
        self._need("ydotool", "install ydotool and run ydotoold (needs /dev/uinput access) for clicks, scroll and drag")
        self._run(["ydotool", *args])

    # --- actions, mirroring the PyAutoGUI calls ActionExecutor used ---

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        self._need("grim", "install grim for screenshots")
        argv = ["grim"]
        if region:
            left, top, width, height = region
            argv += ["-g", f"{left},{top} {width}x{height}"]
        png = self._run(argv + ["-"])
        return Image.open(io.BytesIO(png)).convert("RGB")

    def move(self, x: int, y: int) -> None:
        self._need("hyprctl", "cursor moves use Hyprland's hyprctl")
        x, y = int(x), int(y)
        try:
            # Hyprland with the Lua config evaluates dispatch arguments as Lua
            self._run(["hyprctl", "dispatch", f"hl.dsp.cursor.move({{x={x}, y={y}}})"])
        except RuntimeError:
            self._run(["hyprctl", "dispatch", "movecursor", str(x), str(y)])

    def click(self, x: Optional[int], y: Optional[int], button: str = "left", clicks: int = 1) -> None:
        if x is not None and y is not None:
            self.move(x, y)
        code = BUTTONS.get(button, BUTTONS["left"]) | PRESS | RELEASE
        args = ["click"]
        if clicks > 1:
            args += ["--repeat", str(int(clicks))]
        self._ydotool(*args, hex(code))

    def write(self, text: str) -> None:
        self._need("wtype", "install wtype for typing")
        if text:
            self._run(["wtype", "--", text])

    def press(self, key: str, modifiers: Sequence[str] = ()) -> None:
        self._need("wtype", "install wtype for key presses")
        argv: List[str] = ["wtype"]
        mods = [MODIFIERS.get(m.lower(), m.lower()) for m in modifiers]
        for mod in mods:
            argv += ["-M", mod]
        argv += ["-k", wtype_key_name(key)]
        for mod in reversed(mods):
            argv += ["-m", mod]
        self._run(argv)

    def scroll(self, amount: int, x: Optional[int] = None, y: Optional[int] = None) -> None:
        if x is not None and y is not None:
            self.move(x, y)
        # PyAutoGUI: positive scrolls up. ydotool wheel: positive y scrolls down.
        self._ydotool("mousemove", "--wheel", "-x", "0", "-y", str(-int(amount)))

    def drag(self, dx: int, dy: int, button: str = "left") -> None:
        """Relative drag from the current cursor position, like pyautogui.drag."""
        code = BUTTONS.get(button, BUTTONS["left"])
        self._ydotool("click", hex(code | PRESS))
        try:
            self._ydotool("mousemove", "-x", str(int(dx)), "-y", str(int(dy)))
        finally:
            self._ydotool("click", hex(code | RELEASE))

    def size(self) -> Tuple[int, int]:
        """Size of the focused monitor in logical pixels."""
        import json

        self._need("hyprctl", "screen size comes from hyprctl")
        monitors = json.loads(self._run(["hyprctl", "monitors", "-j"]))
        focused = next((m for m in monitors if m.get("focused")), monitors[0])
        scale = float(focused.get("scale", 1) or 1)
        return int(focused["width"] / scale), int(focused["height"] / scale)

    def execute(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run one ActionExecutor action; same result shape as the PyAutoGUI path."""
        if action_type == "click":
            x, y = params["x"], params["y"]
            button, clicks = params.get("button", "left"), params.get("clicks", 1)
            self.click(x, y, button=button, clicks=clicks)
            return {"status": "success", "action": "click", "coords": (x, y), "button": button, "clicks": clicks}
        if action_type == "type":
            self.write(params["text"])
            return {"status": "success", "action": "type", "text": params["text"]}
        if action_type == "key":
            self.press(params["key"], params.get("modifiers", []))
            return {"status": "success", "action": "key", "key": params["key"]}
        if action_type == "scroll":
            self.scroll(params["amount"], params.get("x"), params.get("y"))
            return {"status": "success", "action": "scroll", "amount": params["amount"]}
        if action_type == "move":
            self.move(params["x"], params["y"])
            return {"status": "success", "action": "move", "coords": (params["x"], params["y"])}
        if action_type == "drag":
            self.drag(params["x"], params["y"], button=params.get("button", "left"))
            return {"status": "success", "action": "drag", "coords": (params["x"], params["y"])}
        raise ValueError(f"Wayland backend does not handle {action_type!r}")
