import webview, threading, time, os, sys, json, subprocess
from pathlib import Path

BASE = Path(__file__).parent
STATIC = BASE / "static"

# ── Calendar engine (lazy init) ───────────────────────────
_calendar = None
_music = None
_web = None
_vision = None
_notes = None
_git = None
_memory = None
_scheduler = None

def get_calendar():
    global _calendar
    if _calendar is None:
        from calendar_engine import CalendarEngine
        _calendar = CalendarEngine()
    return _calendar

def get_music():
    global _music
    if _music is None:
        from music_controller import MusicController
        _music = MusicController()
    return _music

def get_web():
    global _web
    if _web is None:
        from web_agent import WebAgent
        _web = WebAgent()
    return _web

def get_vision():
    global _vision
    if _vision is None:
        from vision_agent import VisionAgent
        _vision = VisionAgent()
    return _vision

def get_notes():
    global _notes
    if _notes is None:
        from notes_engine import NotesEngine
        _notes = NotesEngine()
    return _notes

def get_git():
    global _git
    if _git is None:
        from git_agent import GitAgent
        _git = GitAgent()
    return _git

def get_memory():
    global _memory
    if _memory is None:
        from obsidian_memory import ObsidianMemory
        _memory = ObsidianMemory()
    return _memory

def get_scheduler():
    global _scheduler
    if _scheduler is None:
        from scheduler import SmartScheduler
        _scheduler = SmartScheduler()
        _scheduler.start()
    return _scheduler

# ── Lazy Flask server ──────────────────────────────────────────
_flask_thread = None
_flask_ready = False

def _start_flask():
    global _flask_ready
    from friday_server import app, socketio, start_background_threads
    start_background_threads()
    socketio.run(app, host="127.0.0.1", port=5050, debug=False, use_reloader=False)

def ensure_flask():
    global _flask_thread, _flask_ready
    if _flask_ready:
        return True
    if _flask_thread is None:
        _flask_thread = threading.Thread(target=_start_flask, daemon=True)
        _flask_thread.start()
        for _ in range(50):
            try:
                import urllib.request
                urllib.request.urlopen("http://127.0.0.1:5050/api/health", timeout=1)
                _flask_ready = True
                return True
            except:
                time.sleep(0.1)
    return False

# ── Local-only API (JS Bridge, no server needed) ───────────────
class FridayAPI:
    def get_system_stats(self):
        import psutil
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.usage("/")
            bat = psutil.sensors_battery()
            return json.dumps({
                "cpu": cpu, "mem_percent": mem.percent, "mem_used": round(mem.used / 1e9, 1),
                "disk_percent": disk.percent, "disk_used": round(disk.used / 1e9, 1),
                "battery": bat.percent if bat else None,
            })
        except: return json.dumps({"error": "stats unavailable"})

    def run_scene(self, name):
        from mac_automation import run_scene, SCENES
        if name in SCENES:
            run_scene(name)
            self._notify("FRIDAY Scene", f"{SCENES[name].get('label', name)} activated")
            return json.dumps({"status": "running", "scene": name})
        return json.dumps({"status": "unknown", "scene": name})

    def get_scenes(self):
        from mac_automation import SCENES
        return json.dumps([{"id": k, "name": v.get("label", k), "actions": len(v.get("actions", []))} for k, v in SCENES.items()])

    def get_frontmost_app(self):
        try:
            r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
                             capture_output=True, text=True, timeout=3)
            return r.stdout.strip() or "Friday"
        except: return "Friday"

    def open_app(self, name):
        from mac_automation import open_app as oa
        oa(name)
        return json.dumps({"opened": name})

    def set_volume(self, level):
        from mac_automation import set_volume
        set_volume(int(level))
        return json.dumps({"volume": level})

    def set_brightness(self, level):
        from mac_automation import set_brightness
        set_brightness(int(level))
        return json.dumps({"brightness": level})

    def lock_screen(self):
        from mac_automation import lock_screen
        lock_screen()
        return json.dumps({"status": "locked"})

    def tile_window(self, direction):
        from mac_automation import tile_window_left, tile_window_right
        tile_window_left() if direction == "left" else tile_window_right()
        return json.dumps({"tiled": direction})

    def get_clipboard(self):
        from clipboard_manager import clip_mgr
        return json.dumps({"entries": clip_mgr.get_history()})

    def copy_clipboard(self, text):
        from clipboard_manager import clip_mgr
        clip_mgr.copy_to_clipboard(text)
        return json.dumps({"status": "copied"})

    def search_files(self, query):
        from file_manager import get_structure
        return json.dumps({"files": get_structure()})

    def is_online(self):
        try:
            import urllib.request
            urllib.request.urlopen("https://1.1.1.1", timeout=2)
            return json.dumps({"online": True})
        except:
            return json.dumps({"online": False})

    def get_omniroute_status(self):
        from omniroute import is_available
        return json.dumps({"available": is_available()})

    def get_proactive_suggestions(self):
        try:
            from proactive_engine import proactive
            if proactive:
                return json.dumps({"suggestions": proactive.get_suggestions()})
        except: pass
        return json.dumps({"suggestions": []})

    # ── Calendar bridge (offline + cloud sync) ──
    def get_calendar_events(self, days="7"):
        cal = get_calendar()
        events = cal.get_events(days=int(days))
        return json.dumps({"events": events, "apple": cal.apple.available, "google": cal.google.available})

    def create_calendar_event(self, title, start_time="", duration="30", location="", notes=""):
        cal = get_calendar()
        if not start_time:
            from datetime import datetime, timedelta
            start_time = (datetime.now() + timedelta(hours=1)).isoformat()
        eid = cal.create_event(title, start_time, int(duration), location, notes)
        self._notify("📅 Event Created", f"{title} at {start_time[:16]}")
        return json.dumps({"id": eid, "title": title, "status": "created"})

    def delete_calendar_event(self, eid):
        cal = get_calendar()
        cal.delete_event(eid)
        return json.dumps({"status": "deleted"})

    def sync_calendar(self):
        cal = get_calendar()
        results = cal.full_sync()
        return json.dumps({"synced": True, "apple": results["apple"], "google": results["google"]})

    def get_today_calendar(self):
        cal = get_calendar()
        events = cal.get_today_summary()
        return json.dumps({"events": events, "count": len(events)})

    def parse_calendar_natural(self, text):
        cal = get_calendar()
        parsed = cal.parse_natural(text)
        return json.dumps(parsed)

    # ── Music bridge ──
    def get_now_playing(self):
        return json.dumps(get_music().get_current_track())

    def music_play(self):
        get_music().play()
        return json.dumps({"status": "playing"})

    def music_pause(self):
        get_music().pause()
        return json.dumps({"status": "paused"})

    def music_next(self):
        get_music().next_track()
        return json.dumps({"status": "next"})

    def music_prev(self):
        get_music().previous_track()
        return json.dumps({"status": "previous"})

    def music_volume(self, level):
        lvl = get_music().set_volume(int(level))
        return json.dumps({"volume": lvl})

    # ── Web Agent bridge ──
    def web_search(self, query):
        agent = get_web()
        results = agent.search_google(query)
        return json.dumps(results)

    def web_search_youtube(self, query):
        agent = get_web()
        results = agent.search_youtube(query)
        return json.dumps(results)

    def web_read_page(self, url):
        agent = get_web()
        result = agent.read_page(url)
        return json.dumps(result)

    # ── Vision bridge ──
    def vision_capture(self):
        agent = get_vision()
        result = agent.capture_screen()
        return json.dumps(result)

    def vision_analyze(self, prompt="What do you see?"):
        agent = get_vision()
        analysis = agent.analyze_with_llm(prompt=prompt)
        return json.dumps({"analysis": analysis})

    def vision_capture_selection(self):
        agent = get_vision()
        result = agent.capture_selection()
        return json.dumps(result)

    def _notify(self, title, msg):
        try:
            subprocess.Popen(["osascript", "-e", f'display notification "{msg}" with title "{title}" sound name "default"'])
        except: pass

    # ── Window controls (frameless) ──
    def win_close(self):
        try:
            import webview as _w
            _w.windows[0].destroy()
        except Exception: pass

    def win_min(self):
        try:
            import webview as _w
            _w.windows[0].minimize()
        except Exception: pass

    def win_max(self):
        try:
            import webview as _w
            _w.windows[0].toggle_fullscreen()
        except Exception: pass

    # ── Notes bridge ──
    def get_notes_list(self):
        return json.dumps(get_notes().all_notes())

    def create_note(self, title, body="", folder=""):
        eid = get_notes().create_local_note(title, body, folder)
        self._notify("📝 Note", title)
        return json.dumps({"id": eid, "title": title})

    def get_apple_notes(self):
        return json.dumps({"notes": get_notes().get_apple_notes()})

    # ── Email bridge ──
    def get_email(self):
        from notes_engine import EmailEngine
        return json.dumps(EmailEngine().all_mail())

    # ── Git bridge ──
    def git_status(self):
        return json.dumps(get_git().status())

    def git_log(self):
        return json.dumps(get_git().log())

    def git_run(self, command):
        import shlex
        result = get_git().run(*shlex.split(command))
        return json.dumps(result)

    def git_confirm(self):
        return json.dumps(get_git().confirm_pending())

    # ── Memory bridge ──
    def memory_search(self, query):
        return json.dumps({"results": get_memory().search(query)})

    def memory_notes(self):
        return json.dumps({"notes": get_memory().list_notes()})

    def memory_read(self, path):
        content = get_memory().read_note(path)
        if content:
            return json.dumps({"content": content})
        return json.dumps({"error": "not found"})

    def memory_write(self, filename, content):
        path = get_memory().write_note(filename, content)
        return json.dumps({"path": path, "status": "saved"})

    # ── Scheduler bridge ──
    def scheduler_list(self):
        return json.dumps({"tasks": get_scheduler().list_tasks()})

    def scheduler_create(self, name, description, trigger_type, trigger_value, action_type, action_config):
        import json as _json
        tid = get_scheduler().add_task(name, description, trigger_type, trigger_value, action_type,
                                        _json.loads(action_config) if isinstance(action_config, str) else action_config)
        return json.dumps({"id": tid})

    def scheduler_delete(self, tid):
        get_scheduler().delete_task(tid)
        return json.dumps({"status": "deleted"})

    def scheduler_toggle(self, tid):
        get_scheduler().toggle_task(tid)
        return json.dumps({"status": "toggled"})

# ── Launch ──────────────────────────────────────────────────────
def main():
    api = FridayAPI()
    index_path = str(STATIC / "mission" / "index.html")

    window = webview.create_window(
        "FRIDAY AI",
        index_path,
        js_api=api,
        width=1440, height=920,
        frameless=True,
        easy_drag=False,
        background_color="#06111D",
    )

    def _init():
        # Boot the Flask core in the background; the UI is already visible
        # via the local file (dedicated-app feel, no localhost address).
        ready = ensure_flask()
        if ready:
            try:
                window.load_url("http://localhost:5050")
            except:
                pass
        else:
            try:
                window.evaluate_js("window.dispatchEvent(new CustomEvent('friday:offline'))")
            except: pass

    threading.Thread(target=_init, daemon=True).start()
    webview.start()

if __name__ == "__main__":
    main()
