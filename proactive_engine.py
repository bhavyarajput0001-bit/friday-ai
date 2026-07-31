import time, threading, random
from datetime import datetime
from mac_automation import get_system_state

class ProactiveEngine:
    def __init__(self, suggestion_callback, scene_callback, store=None):
        self.callback = suggestion_callback
        self.scene_callback = scene_callback
        self.store = store
        self._running = False
        self._thread = None
        self._last_suggestions = []
        self._greeted_today = False
        self._cooldown = {}
        self._last_task_ids = set()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _suggest(self, text, category="info", action=None):
        suggestion = {
            "id": str(int(time.time() * 1000)),
            "text": text,
            "category": category,
            "time": datetime.now().strftime("%I:%M %p"),
            "action": action,
        }
        self._last_suggestions.insert(0, suggestion)
        if len(self._last_suggestions) > 20:
            self._last_suggestions = self._last_suggestions[:20]
        if self.callback:
            self.callback(suggestion)

    def get_suggestions(self):
        return self._last_suggestions[:10]

    def _loop(self):
        time.sleep(5)  # Wait for system to settle
        while self._running:
            try:
                state = get_system_state()
                hour = state.get("hour", 12)
                app = state.get("frontmost_app", "")
                day = state.get("day_name", "")
                is_weekend = state.get("is_weekend", False)

                now_key = f"{datetime.now().hour}:{datetime.now().minute // 15}"
                if self._cooldown.get(now_key):
                    time.sleep(10)
                    continue
                self._cooldown[now_key] = True

                # Morning greeting (once)
                if 7 <= hour <= 10 and not self._greeted_today:
                    self._greeted_today = True
                    greeting = "Good morning!" if hour < 12 else "Good day!"
                    if is_weekend:
                        self._suggest(f"{greeting} It's {day}. Ready to relax?", "greeting")
                    else:
                        self._suggest(f"{greeting} It's {day}. Ready to work?", "greeting")

                # ── Task responsibility: nag about due / in-progress tasks ──
                tasks = []
                if self.store:
                    tasks = self.store.get("tasks", []) or []
                pending = [t for t in tasks if t.get("status") in ("pending", "in_progress", "queued")]
                now_ids = {t.get("id") for t in pending}
                if now_ids and now_ids != self._last_task_ids and len(self._last_task_ids) > 0:
                    new_ids = now_ids - self._last_task_ids
                    fresh = [t for t in pending if t.get("id") in new_ids]
                    if fresh:
                        t = fresh[0]
                        self._suggest(
                            f"New task logged: “{t.get('title')}”. Want me to schedule it?",
                            "task", {"type": "task", "task_id": t.get("id")},
                        )
                self._last_task_ids = now_ids

                # Reminder for in-progress task (once per hour)
                if pending:
                    top = pending[0]
                    task_key = f"task_{top.get('id')}_{datetime.now().hour}"
                    if task_key not in self._cooldown and random.random() < 0.4:
                        self._cooldown[task_key] = True
                        self._suggest(
                            f"Still open: “{top.get('title')}”. Say 'status' and I'll give you the full picture.",
                            "task", {"type": "task", "task_id": top.get("id")},
                        )

                # Agenda awareness: upcoming item within the hour
                if self.store:
                    agenda = self.store.get("agenda", []) or []
                    for item in agenda:
                        try:
                            t = datetime.strptime(item.get("time", ""), "%I:%M %p")
                        except Exception:
                            continue
                        mins_until = (t.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day) - datetime.now()).total_seconds() / 60
                        if 0 < mins_until <= 15:
                            self._suggest(
                                f"Coming up in {int(mins_until)}m: {item.get('title')}. Need anything prepped?",
                                "agenda", {"type": "agenda", "agenda_id": item.get("id")},
                            )
                            break

                # Time-based
                if 12 <= hour <= 13:
                    self._suggest("It's lunch time!", "reminder", {"type": "suggest_scene", "scene": "focus"})

                if 17 <= hour <= 18:
                    self._suggest("Evening winding down. Time to review your day.", "reminder")

                if hour >= 22 or hour <= 5:
                    self._suggest("It's late — should I lock the screen?", "suggestion", {"type": "system", "command": "lock screen"})

                # Context-based: coding
                if "code" in app.lower() or "terminal" in app.lower():
                    self._suggest("Working on code. Need a quick terminal command?", "context", {"type": "suggest_scene", "scene": "coding"})

                # Context-based: browser
                if "safari" in app.lower() or "chrome" in app.lower() or "brave" in app.lower() or "firefox" in app.lower():
                    self._suggest("Researching something? I can take notes.", "context", {"type": "clipboard", "action": "save"})

                # Random deep suggestions (sparse)
                if random.random() < 0.15:
                    tips = [
                        "I can organize your Downloads if it gets messy.",
                        "Try saying 'start coding mode' to launch your workspace.",
                        "Say 'movie mode' to dim lights and open Plex.",
                        "I can search your files — just ask.",
                        "I remember clipboard history. Say 'show clipboard'.",
                        "Hold ⌥ (Option) + Space and talk to me — instant push-to-talk.",
                    ]
                    self._suggest(random.choice(tips), "tip")

                time.sleep(45)

            except Exception as e:
                print(f"[Proactive] Error: {e}")
                time.sleep(30)
