import subprocess, os, json, base64, time, threading
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
SCREENSHOT_DIR = DATA_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

class VisionAgent:
    def __init__(self):
        self._last_screenshot = None
        self._hotkey_active = False
        self._listener_thread = None

    def capture_screen(self, filename=None):
        if filename is None:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = str(SCREENSHOT_DIR / filename)
        try:
            subprocess.run(["screencapture", "-x", path], timeout=5, capture_output=True)
            if os.path.exists(path):
                self._last_screenshot = path
                return {"path": path, "filename": filename, "size": os.path.getsize(path)}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "screenshot failed"}

    def capture_selection(self, filename=None):
        if filename is None:
            filename = f"selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = str(SCREENSHOT_DIR / filename)
        try:
            subprocess.run(["screencapture", "-is", path], timeout=30, capture_output=True)
            if os.path.exists(path) and os.path.getsize(path) > 0:
                self._last_screenshot = path
                return {"path": path, "filename": filename, "size": os.path.getsize(path)}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "selection cancelled or failed"}

    def read_screenshot_base64(self, path=None):
        path = path or self._last_screenshot
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except:
            return None

    def analyze_with_llm(self, path=None, prompt="What do you see in this image?"):
        b64 = self.read_screenshot_base64(path)
        if not b64:
            return "No screenshot available. Take one first."

        try:
            from omniroute import is_available as omni_available, chat as omni_chat
            if omni_available():
                result = omni_chat(messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64[:100000]}"}}
                    ]}
                ], max_tokens=1024)
                if result and result.get("text"):
                    return result["text"]
        except: pass

        try:
            from brain import call_gemini
            return call_gemini(f"{prompt}\n[Image: screenshot attached]")
        except:
            return "Vision: LLM unavailable for image analysis."

    def start_hotkey_listener(self, callback):
        """Monitor for hotkey press (Cmd+Shift+8)."""
        def _listen():
            import Quartz
            from Quartz import (
                CGEventTapCreate, kCGHeadInsertEventTap,
                kCGEventKeyDown, kCGHIDEventTap,
                CGEventTapEnable, CFRunLoopRun
            )

            def handler(proxy, type_, event, refcon):
                if type_ == kCGEventKeyDown:
                    flags = Quartz.CGEventGetFlags(event)
                    key = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
                    # Cmd+Shift+8 (keycode 28)
                    cmd = flags & Quartz.kCGEventFlagMaskCommand
                    shift = flags & Quartz.kCGEventFlagMaskShift
                    if cmd and shift and key == 28:
                        result = self.capture_screen()
                        if "path" in result:
                            analysis = self.analyze_with_llm(result["path"])
                            if callback:
                                callback({"screenshot": result, "analysis": analysis})
                return event

            tap = CGEventTapCreate(
                kCGHIDEventTap, kCGHeadInsertEventTap, 0,
                (1 << kCGEventKeyDown), handler, None
            )
            if tap:
                CGEventTapEnable(tap, True)
                CFRunLoopRun()

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()
        return True

    def get_recent_screenshots(self, count=5):
        files = sorted(SCREENSHOT_DIR.glob("*.png"), key=os.path.getmtime, reverse=True)
        return [{"path": str(f), "name": f.name, "size": f.stat().st_size, "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat()} for f in files[:count]]
