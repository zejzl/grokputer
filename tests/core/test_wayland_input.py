"""Wayland backend: command lines it builds, backend selection, missing tools."""

import io
import json

import pytest
from PIL import Image

from src.core.wayland_input import WaylandInput, WaylandInputUnavailable, backend_name


def _png(width=4, height=3):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buffer, format="PNG")
    return buffer.getvalue()


class Recorder:
    def __init__(self, output=b""):
        self.calls = []
        self.output = output

    def __call__(self, argv):
        self.calls.append(list(argv))
        return self.output


def _backend(output=b"", missing=()):
    run = Recorder(output)
    which = lambda tool: None if tool in missing else f"/usr/bin/{tool}"  # noqa: E731
    return WaylandInput(run=run, which=which), run


def test_backend_selection():
    assert backend_name({"GROKPUTER_INPUT_BACKEND": "pyautogui", "WAYLAND_DISPLAY": "wayland-1"}) == "pyautogui"
    assert backend_name({"GROKPUTER_INPUT_BACKEND": "wayland"}) == "wayland"
    assert backend_name({}) == "pyautogui"


def test_screenshot_full_and_region():
    backend, run = _backend(output=_png())
    image = backend.screenshot()
    assert image.size == (4, 3)
    assert run.calls[-1] == ["grim", "-"]
    backend.screenshot((10, 20, 300, 200))
    assert run.calls[-1] == ["grim", "-g", "10,20 300x200", "-"]


def test_click_moves_then_clicks():
    backend, run = _backend()
    backend.click(100, 200, button="right", clicks=2)
    assert run.calls == [
        ["hyprctl", "dispatch", "hl.dsp.cursor.move({x=100, y=200})"],
        ["ydotool", "click", "--repeat", "2", "0xc1"],
    ]


def test_move_falls_back_to_legacy_dispatch():
    calls = []

    def run(argv):
        calls.append(list(argv))
        if "hl.dsp" in argv[-1]:
            raise RuntimeError("hyprctl failed: unknown dispatcher")
        return b""

    WaylandInput(run=run, which=lambda tool: f"/usr/bin/{tool}").move(5, 6)
    assert calls[-1] == ["hyprctl", "dispatch", "movecursor", "5", "6"]


def test_type_and_hotkey():
    backend, run = _backend()
    backend.write("Hello World")
    backend.press("c", ["ctrl"])
    backend.press("enter")
    assert run.calls == [
        ["wtype", "--", "Hello World"],
        ["wtype", "-M", "ctrl", "-k", "c", "-m", "ctrl"],
        ["wtype", "-k", "Return"],
    ]


def test_scroll_up_is_negative_wheel():
    backend, run = _backend()
    backend.scroll(3)
    assert run.calls == [["ydotool", "mousemove", "--wheel", "-x", "0", "-y", "-3"]]


def test_drag_presses_moves_and_releases():
    backend, run = _backend()
    backend.drag(50, -10)
    assert run.calls == [
        ["ydotool", "click", "0x40"],
        ["ydotool", "mousemove", "-x", "50", "-y", "-10"],
        ["ydotool", "click", "0x80"],
    ]


def test_missing_ydotool_names_the_fix():
    backend, _ = _backend(missing=("ydotool",))
    with pytest.raises(WaylandInputUnavailable, match="ydotool"):
        backend.click(1, 2)


def test_size_uses_focused_monitor_and_scale():
    monitors = [{"focused": False, "width": 800, "height": 600, "scale": 1},
                {"focused": True, "width": 2560, "height": 1440, "scale": 2}]
    backend, _ = _backend(output=json.dumps(monitors).encode())
    assert backend.size() == (1280, 720)


def test_execute_matches_pyautogui_result_shape():
    backend, _ = _backend()
    result = backend.execute("click", {"x": 1, "y": 2})
    assert result == {"status": "success", "action": "click", "coords": (1, 2), "button": "left", "clicks": 1}
