import subprocess, time, threading, json, os
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
CLIP_FILE = DATA_DIR / "clipboard_history.json"

MAX_HISTORY = 50

class ClipboardManager:
    def __init__(self):
        self.history = self._load()
        self._last_content = self._get_clipboard()
        self._running = False
        self._thread = None

    def _load(self):
        if CLIP_FILE.exists():
            try: return json.load(open(CLIP_FILE))
            except: pass
        return {"entries": [], "snippets": {}}

    def _save(self):
        DATA_DIR.mkdir(exist_ok=True)
        json.dump(self.history, open(CLIP_FILE, "w"), indent=2)

    def _get_clipboard(self):
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=2)
            return result.stdout
        except:
            return ""

    def _set_clipboard(self, text):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode())
        except:
            pass

    def start_monitoring(self, callback=None):
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        self._running = False

    def _monitor_loop(self, callback=None):
        while self._running:
            try:
                current = self._get_clipboard()
                if current and current != self._last_content and len(current.strip()) > 0:
                    self._last_content = current
                    entry = {
                        "id": str(int(time.time() * 1000)),
                        "text": current[:200],
                        "full_text": current[:2000],
                        "time": datetime.now().strftime("%I:%M %p"),
                        "length": len(current),
                    }
                    self.history["entries"].insert(0, entry)
                    if len(self.history["entries"]) > MAX_HISTORY:
                        self.history["entries"] = self.history["entries"][:MAX_HISTORY]
                    self._save()
                    if callback:
                        callback(entry)
            except:
                pass
            time.sleep(1.5)

    def get_history(self, limit=20):
        return self.history["entries"][:limit]

    def copy_to_clipboard(self, text):
        self._set_clipboard(text)
        self._last_content = text
        return {"text": text[:100], "time": datetime.now().strftime("%I:%M %p")}

    def save_snippet(self, name, text):
        self.history["snippets"][name] = {
            "text": text,
            "time": datetime.now().strftime("%I:%M %p"),
        }
        self._save()
        return {"name": name, "text": text[:100]}

    def get_snippet(self, name):
        return self.history["snippets"].get(name)

    def list_snippets(self):
        return list(self.history["snippets"].keys())

    def delete_snippet(self, name):
        if name in self.history["snippets"]:
            del self.history["snippets"][name]
            self._save()
            return True
        return False
