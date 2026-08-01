#!/usr/bin/env python3
"""
Friday AI — JARVIS-Style HUD Dashboard
Backend server: Flask + SocketIO + System Monitor + Voice + Browser Control
"""

import os, sys, json, threading, time, subprocess, re, urllib.parse, uuid, shlex
from pathlib import Path
from datetime import datetime

# ── Flask + SocketIO ──────────────────────────────────────────────────────────
from flask import Flask, send_from_directory, request
from flask_socketio import SocketIO, emit
import psutil

# ── Friday Core Upgrades ──────────────────────────────────────────────────────
from database import FridayDB
from context_manager import FridayContext
from file_manager import get_structure, get_file_counts
from mac_automation import (
    set_volume, set_brightness, set_dark_mode, lock_screen, sleep_display,
    empty_trash, tile_window_left, tile_window_right, fullscreen_app,
    show_desktop, minimize_all, open_app as mac_open_app,
    SCENES, run_scene, get_system_state, get_frontmost_app,
)
from clipboard_manager import ClipboardManager
from proactive_engine import ProactiveEngine
from command_router import parse_command
from omniroute import is_available as omni_available, set_key as omni_set_key

clip_mgr = ClipboardManager()
proactive = None  # initialized in start_background_threads
db = FridayDB()
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
        _scheduler.start(callback=scheduler_callback)
    return _scheduler

def scheduler_callback(task, config):
    try:
        name = task.get("name", "Task")
        action = task.get("action_type", "notify")
        push_message(f"⏰ **{name}** triggered")
        if action == "notify":
            send_notification("FRIDAY Scheduler", f"{name}")
        elif action == "open_app":
            app = (config or {}).get("app", "")
            if app:
                mac_open_app(app)
        elif action == "run_scene":
            scene = (config or {}).get("scene", "")
            if scene in SCENES:
                run_scene(scene)
        elif action == "send_message":
            msg = (config or {}).get("message", "")
            if msg:
                push_message(f"📬 Scheduled: {msg}")
        elif action == "run_command":
            cmd = (config or {}).get("command", "")
            if cmd:
                process_command(cmd)
    except Exception as e:
        print(f"[Scheduler] Error: {e}")

# ── Multi-LLM Brain ───────────────────────────────────────────────────────────
from brain import process_with_brain

# ── Optional imports ──────────────────────────────────────────────────────────
VOICE_OK = False
try:
    import speech_recognition as sr
    import audioop
    VOICE_OK = True
except ImportError:
    print("[WARN] speech_recognition / pyaudio not found — voice disabled")

TRANSLATE_OK = False
try:
    from deep_translator import GoogleTranslator
    TRANSLATE_OK = True
except ImportError:
    print("[WARN] deep-translator not found — translation disabled")

PLAYWRIGHT_OK = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    print("[WARN] playwright not found — browser commands disabled")

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG & PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════
HOME = Path.home()
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MEM_FILE = DATA_DIR / "friday_memory.json"

DEFAULT_CFG = {
    "mode": "interact",
    "voice_index": "siri",
    "speak_on": False,
    "clap_trigger": False,
    "wake_word": "friday",
    "clap_thresh": 2000,
    "listen_timeout": 4,
    "continuous_listen": False,
}

DEFAULT_DATA = {
    "cfg": DEFAULT_CFG.copy(),
    "custom_cmds": {},
    "tasks": [
        {"id": "t1", "title": "Finish Friday UI Design", "status": "in_progress", "progress": 65, "priority": "high", "due": "Online"},
        {"id": "t2", "title": "Review Code Repository", "status": "pending", "progress": 0, "priority": "medium", "due": "Due 3:00 PM"},
        {"id": "t3", "title": "Backup Important Files", "status": "queued", "progress": 0, "priority": "low", "due": "Queued"},
    ],
    "agenda": [
        {"id": "a1", "time": "9:00 AM", "title": "Gym & Training", "duration": "1h"},
        {"id": "a2", "time": "11:30 AM", "title": "Project Friday UI", "duration": "", "highlight": True},
        {"id": "a3", "time": "3:00 PM", "title": "Meeting – Team Sync", "duration": "30m"},
        {"id": "a4", "time": "7:00 PM", "title": "Personal Time", "duration": "2h"},
    ],
    "knowledge": {
        "projects": {"count": 22, "label": "Files"},
        "notes": {"count": 128, "label": "Items"},
        "research": {"count": 14, "label": "Sources"},
        "voice_memos": {"count": 9, "label": "Recordings"},
    },
    "automations": [
        {"id": "auto1", "name": "Morning Briefing", "schedule": "7:00 AM Daily", "enabled": True, "icon": "📋"},
        {"id": "auto2", "name": "Focus Mode", "schedule": "On Schedule", "enabled": True, "icon": "🎯"},
        {"id": "auto3", "name": "File Backup", "schedule": "Every 6 Hours", "enabled": False, "icon": "💾"},
        {"id": "auto4", "name": "Nightly Shutdown", "schedule": "12:00 AM", "enabled": False, "icon": "🌙"},
    ],
    "productivity": {"today": 87},
    "conversation": [],
}


def load_memory():
    if MEM_FILE.exists():
        try:
            return json.load(open(MEM_FILE, "r"))
        except Exception:
            pass
    return DEFAULT_DATA.copy()


def save_memory():
    json.dump(store, open(MEM_FILE, "w"), indent=2, default=str)


store = load_memory()
# Ensure all keys exist
for k, v in DEFAULT_DATA.items():
    if k not in store:
        store[k] = v
cfg = store.get("cfg", DEFAULT_CFG.copy())
custom_cmds = store.get("custom_cmds", {})

# ══════════════════════════════════════════════════════════════════════════════
#  UI REGISTRY — every FRIDAY interface that can be previewed & switched
#  ══════════════════════════════════════════════════════════════════════════════
UI_REGISTRY = [
    {
        "id": "mission",
        "name": "FRIDAY OS",
        "version": "2.0",
        "desc": "Apple-grade AI operating system — deep-navy glass, 60fps AI core, modular workspace.",
        "path": "/",
        "kind": "current",
    },
    {
        "id": "legacy",
        "name": "Legacy Dashboard",
        "version": "1.x",
        "desc": "The original FRIDAY HUD dashboard — everything panel, clipboards, automations.",
        "path": "/dashboard",
        "kind": "legacy",
    },
    {
        "id": "pwa",
        "name": "PWA Shell",
        "version": "1.x",
        "desc": "Progressive web app shell for installing FRIDAY as a standalone web app.",
        "path": "/pwa/",
        "kind": "alternate",
    },
]

def get_active_ui():
    """Active UI id, persisted in memory store."""
    active = store.get("active_ui", "mission")
    if active not in {u["id"] for u in UI_REGISTRY}:
        active = "mission"
    return active

def set_active_ui(ui_id):
    if ui_id not in {u["id"] for u in UI_REGISTRY}:
        return False
    store["active_ui"] = ui_id
    save_memory()
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  FLASK APP
# ══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder="static", static_url_path="")
app.config["SECRET_KEY"] = "friday-jarvis-2024"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Serve the active UI at /
@app.route("/")
def index():
    active = get_active_ui()
    if active == "mission":
        return send_from_directory("static/mission", "index.html")
    if active == "pwa":
        return send_from_directory("static/pwa", "index.html")
    return send_from_directory("static", "index.html")

# ── UI Registry API ──
@app.route("/api/ui")
def api_ui_list():
    active = get_active_ui()
    uis = []
    for u in UI_REGISTRY:
        item = dict(u)
        item["active"] = (u["id"] == active)
        uis.append(item)
    return {"uis": uis, "active": active}

@app.route("/api/ui/activate", methods=["POST"])
def api_ui_activate():
    data = request.get_json() or {}
    ui_id = data.get("id", "")
    if set_active_ui(ui_id):
        u = next((x for x in UI_REGISTRY if x["id"] == ui_id), {})
        socketio.emit("ui:state", {"active": ui_id, "path": u.get("path", "/")})
        return {"ok": True, "active": ui_id, "path": u.get("path", "/")}
    return {"ok": False, "error": "unknown ui id"}, 400

@app.route("/dashboard")
def dashboard():
    return send_from_directory("static", "index.html")

@app.route("/screenshots/<path:filename>")
def screenshots(filename):
    return send_from_directory("data/screenshots", filename)

@app.route("/pwa/")
@app.route("/pwa/<path:filename>")
def pwa_app(filename="index.html"):
    return send_from_directory("static/pwa", filename)

# ── REST API ──
@app.route("/api/health")
def api_health():
    return {"status": "ok", "version": "4.0", "services": {
        "omniroute": omni_available(), "clipboard": True, "scenes": len(SCENES),
        "music": True, "web": get_web().available, "vision": True, "calendar": True,
        "notes": True, "email": True, "git": True, "memory": True, "scheduler": True
    }}

@app.route("/api/status")
def api_status():
    import psutil
    cpu = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    return {
        "cpu": cpu, "mem_percent": mem.percent, "mem_used": round(mem.used / 1e9, 1),
        "disk_percent": disk.percent, "disk_used": round(disk.used / 1e9, 1),
        "battery": psutil.sensors_battery().percent if psutil.sensors_battery() else None,
    }

# ── Chat response collector (for /api/chat) ───────────────────────────────
_chat_lock = threading.Lock()
_chat_active = False
_chat_collect = []


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    text = data.get("text", "")
    if not text:
        return {"error": "text field required"}, 400
    with _chat_lock:
        global _chat_collect, _chat_active
        _chat_active = True
        _chat_collect = []
        try:
            process_command(text)
            # Wait (bounded) for the real FRIDAY reply. Interim "Routing: …"
            # headers arrive first; the final answer follows from the LLM.
            for _ in range(150):  # up to 15s
                if _chat_collect and not _chat_collect[-1].startswith("Routing:"):
                    break
                time.sleep(0.1)
            return {"response": _chat_collect[-1] if _chat_collect else "Processed", "interim": list(_chat_collect)}
        finally:
            _chat_active = False
            _chat_collect = []

# ── Push-to-Talk ──────────────────────────────────────────────────────────────
ptt_active = False
ptt_frames = []
ptt_lock = threading.Lock()
PTT_RATE = 16000
PTT_CHANNELS = 1


def ptt_start():
    """Begin push-to-talk capture (hold ⌥+Space while speaking)."""
    global ptt_active, ptt_frames
    if not VOICE_OK:
        push_message("Voice not available — install speechrecognition + pyaudio")
        return {"ok": False, "error": "voice unavailable"}
    with ptt_lock:
        if ptt_active:
            return {"ok": True, "already": True}
        ptt_active = True
        ptt_frames = []
    push_message("Push-to-talk active — speak now.")
    socketio.emit("voice:status", {"state": "listening"})
    threading.Thread(target=_ptt_capture_loop, daemon=True).start()
    return {"ok": True}


def _ptt_capture_loop():
    import pyaudio
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=pyaudio.paInt16, channels=PTT_CHANNELS,
                        rate=PTT_RATE, input=True, frames_per_buffer=2048)
    except Exception as e:
        print("[PTT] mic error:", e)
        push_message("Microphone error")
        return
    try:
        while True:
            with ptt_lock:
                if not ptt_active:
                    break
            try:
                data = stream.read(2048, exception_on_overflow=False)
                with ptt_lock:
                    ptt_frames.append(data)
                rms = audioop.rms(data, 2)
                socketio.emit("voice:waveform", {"rms": rms})
            except Exception:
                break
    finally:
        stream.stop_stream(); stream.close(); p.terminate()


def ptt_stop():
    """Finish push-to-talk: stop capture, transcribe, process command."""
    global ptt_active, ptt_frames
    with ptt_lock:
        if not ptt_active:
            return {"ok": False, "error": "not active"}
        ptt_active = False
        frames = list(ptt_frames)
        ptt_frames = []
    socketio.emit("voice:status", {"state": "processing"})
    time.sleep(0.4)
    if not frames:
        socketio.emit("voice:status", {"state": "idle"})
        push_message("Didn't catch that")
        return {"ok": True, "text": ""}
    raw = b"".join(frames)
    audio = sr.AudioData(raw, PTT_RATE, 2)
    text = recognize_audio(audio)
    if text:
        push_message(text, sender="user")
        threading.Thread(target=process_command, args=(text,), daemon=True).start()
    else:
        push_message("Didn't catch that")
    socketio.emit("voice:status", {"state": "idle"})
    return {"ok": True, "text": text}


@app.route("/api/voice/ptt", methods=["POST"])
def api_voice_ptt():
    data = request.get_json() or {}
    action = data.get("action", "")
    if action == "start":
        return ptt_start()
    if action == "stop":
        return ptt_stop()
    if action == "status":
        import os as _os
        ptt_bin = Path(__file__).parent / "ptt_hotkey"
        running = any("ptt_hotkey" in (p or "") for p in (_os.popen("pgrep -fl ptt_hotkey").read() or "").splitlines())
        return {"ok": running and ptt_bin.exists(), "helper": str(ptt_bin)}
    if action == "ptt_hotkey" and data.get("enable"):
        try:
            ptt_bin = Path(__file__).parent / "ptt_hotkey"
            if not ptt_bin.exists():
                return {"ok": False, "error": "helper not built"}
            subprocess.Popen([str(ptt_bin)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return {"error": "unknown action"}, 400


@app.route("/api/tasks", methods=["GET", "POST"])
def api_tasks():
    if request.method == "POST":
        data = request.get_json() or {}
        db.add_task(data.get("title", ""), data.get("priority", "medium"), data.get("due", ""))
        return {"status": "created"}
    return {"tasks": db.get_tasks()}

@app.route("/api/agenda", methods=["GET", "POST"])
def api_agenda():
    if request.method == "POST":
        data = request.get_json() or {}
        db.add_agenda(data.get("time", ""), data.get("title", ""), data.get("duration", ""))
        return {"status": "created"}
    return {"items": db.get_agenda()}

@app.route("/api/knowledge")
def api_knowledge():
    return {"knowledge": store.get("knowledge", {})}

@app.route("/api/files")
def api_files():
    return get_structure()

@app.route("/api/scenes")
def api_scenes():
    return {"scenes": [{"id": k, "name": v.get("label", k), "actions": len(v.get("actions", []))} for k, v in SCENES.items()]}

@app.route("/api/scenes/run", methods=["POST"])
def api_scene_run():
    data = request.get_json() or {}
    scene = data.get("scene", "")
    if scene in SCENES:
        run_scene(scene)
        return {"status": "running", "scene": scene}
    return {"error": f"Scene '{scene}' not found"}, 404

@app.route("/api/clipboard")
def api_clipboard():
    return {"entries": clip_mgr.get_history()}

@app.route("/api/clipboard/copy", methods=["POST"])
def api_clipboard_copy():
    data = request.get_json() or {}
    text = data.get("text", "")
    if text:
        result = clip_mgr.copy_to_clipboard(text)
        return {"status": "copied", "text": result["text"]}
    return {"error": "text field required"}, 400

@app.route("/api/omniroute/key", methods=["POST"])
def api_omniroute_set_key():
    data = request.get_json() or {}
    key = data.get("key", "")
    if key:
        omni_set_key(key)
        return {"status": "set", "available": True}
    return {"error": "key required"}, 400

@app.route("/api/omniroute/status")
def api_omniroute_status():
    return {"available": omni_available(), "tier": "cheap"}

# ── Calendar REST API ──
@app.route("/api/calendar/events")
def api_calendar_events():
    cal = get_calendar()
    days = request.args.get("days", 7, type=int)
    events = cal.get_events(days=days)
    return {"events": events, "apple": cal.apple.available, "google": cal.google.available}

@app.route("/api/calendar/today")
def api_calendar_today():
    cal = get_calendar()
    events = cal.get_today_summary()
    return {"events": events, "count": len(events)}

@app.route("/api/calendar/create", methods=["POST"])
def api_calendar_create():
    data = request.get_json() or {}
    cal = get_calendar()
    eid = cal.create_event(
        data.get("title", "Event"),
        data.get("start_time", ""),
        data.get("duration", 30),
        data.get("location", ""),
        data.get("notes", ""),
    )
    return {"id": eid, "status": "created"}

@app.route("/api/calendar/delete", methods=["POST"])
def api_calendar_delete():
    data = request.get_json() or {}
    cal = get_calendar()
    cal.delete_event(data.get("id", ""))
    return {"status": "deleted"}

@app.route("/api/calendar/sync", methods=["POST"])
def api_calendar_sync():
    cal = get_calendar()
    results = cal.full_sync()
    return {"synced": True, "apple": results["apple"], "google": results["google"]}

# ── Music REST API ──
@app.route("/api/music/now")
def api_music_now():
    return get_music().get_current_track()

@app.route("/api/music/play", methods=["POST"])
def api_music_play():
    get_music().play()
    return {"status": "playing"}

@app.route("/api/music/pause", methods=["POST"])
def api_music_pause():
    get_music().pause()
    return {"status": "paused"}

@app.route("/api/music/next", methods=["POST"])
def api_music_next():
    get_music().next_track()
    return {"status": "next"}

@app.route("/api/music/prev", methods=["POST"])
def api_music_prev():
    get_music().previous_track()
    return {"status": "previous"}

@app.route("/api/music/volume", methods=["POST"])
def api_music_volume():
    data = request.get_json() or {}
    lvl = get_music().set_volume(data.get("level", 50))
    return {"volume": lvl}

@app.route("/api/music/open", methods=["POST"])
def api_music_open():
    get_music().open_music()
    return {"status": "opened"}

# ── Web Agent REST API ──
@app.route("/api/web/search", methods=["POST"])
def api_web_search():
    data = request.get_json() or {}
    query = data.get("query", "")
    if not query: return {"error": "query required"}, 400
    agent = get_web()
    results = agent.search_google(query)
    return results

@app.route("/api/web/search_youtube", methods=["POST"])
def api_web_search_youtube():
    data = request.get_json() or {}
    query = data.get("query", "")
    if not query: return {"error": "query required"}, 400
    agent = get_web()
    results = agent.search_youtube(query)
    return results

@app.route("/api/web/read", methods=["POST"])
def api_web_read():
    data = request.get_json() or {}
    url = data.get("url", "")
    if not url: return {"error": "url required"}, 400
    agent = get_web()
    return agent.read_page(url)

# ── Vision REST API ──
@app.route("/api/vision/capture", methods=["POST"])
def api_vision_capture():
    agent = get_vision()
    result = agent.capture_screen()
    return result

@app.route("/api/vision/capture_selection", methods=["POST"])
def api_vision_capture_selection():
    agent = get_vision()
    result = agent.capture_selection()
    return result

@app.route("/api/vision/analyze", methods=["POST"])
def api_vision_analyze():
    data = request.get_json() or {}
    agent = get_vision()
    analysis = agent.analyze_with_llm(prompt=data.get("prompt", "What do you see?"))
    return {"analysis": analysis}

# ── Notes REST API ──
@app.route("/api/notes", methods=["GET", "POST"])
def api_notes():
    if request.method == "POST":
        data = request.get_json() or {}
        eid = get_notes().create_local_note(data.get("title", ""), data.get("body", ""), data.get("folder", ""))
        return {"id": eid, "status": "created"}
    return {"notes": get_notes().all_notes()}

@app.route("/api/notes/apple")
def api_notes_apple():
    return {"notes": get_notes().get_apple_notes()}

@app.route("/api/notes/keep")
def api_notes_keep():
    return {"notes": get_notes().get_keep_notes()}

@app.route("/api/notes/create", methods=["POST"])
def api_notes_create():
    data = request.get_json() or {}
    eid = get_notes().create_local_note(data.get("title", ""), data.get("body", ""), data.get("folder", ""))
    return {"id": eid, "status": "created"}

# ── Email REST API ──
@app.route("/api/email")
def api_email():
    from notes_engine import EmailEngine
    eng = EmailEngine()
    return eng.all_mail()

# ── Git Agent REST API ──
@app.route("/api/git/status")
def api_git_status():
    return get_git().status()

@app.route("/api/git/log")
def api_git_log():
    return get_git().log()

@app.route("/api/git/diff")
def api_git_diff():
    return get_git().diff()

@app.route("/api/git/run", methods=["POST"])
def api_git_run():
    data = request.get_json() or {}
    git = get_git()
    return git.run(*shlex.split(data.get("command", "")))

@app.route("/api/git/confirm", methods=["POST"])
def api_git_confirm():
    return get_git().confirm_pending()

@app.route("/api/git/cancel", methods=["POST"])
def api_git_cancel():
    return get_git().cancel_pending()

# ── Obsidian Memory REST API ──
@app.route("/api/memory/search")
def api_memory_search():
    query = request.args.get("q", "")
    if not query:
        return {"results": []}
    return {"results": get_memory().search(query)}

@app.route("/api/memory/notes")
def api_memory_notes():
    folder = request.args.get("folder", "")
    return {"notes": get_memory().list_notes(folder)}

@app.route("/api/memory/read")
def api_memory_read():
    file = request.args.get("file", "")
    if not file:
        return {"error": "file required"}, 400
    content = get_memory().read_note(file)
    if content is None:
        return {"error": "not found"}, 404
    return {"content": content}

@app.route("/api/memory/write", methods=["POST"])
def api_memory_write():
    data = request.get_json() or {}
    path = get_memory().write_note(data.get("filename", "note.md"), data.get("content", ""))
    return {"path": path, "status": "saved"}

# ── Scheduler REST API ──
@app.route("/api/scheduler/tasks")
def api_scheduler_tasks():
    return {"tasks": get_scheduler().list_tasks()}

@app.route("/api/scheduler/create", methods=["POST"])
def api_scheduler_create():
    data = request.get_json() or {}
    tid = get_scheduler().add_task(
        data.get("name", "Task"), data.get("description", ""),
        data.get("trigger_type", "interval"), data.get("trigger_value", "30m"),
        data.get("action_type", "notify"), data.get("action_config", {}))
    return {"id": tid, "status": "created"}

@app.route("/api/scheduler/delete", methods=["POST"])
def api_scheduler_delete():
    data = request.get_json() or {}
    get_scheduler().delete_task(data.get("id", 0))
    return {"status": "deleted"}

@app.route("/api/scheduler/toggle", methods=["POST"])
def api_scheduler_toggle():
    data = request.get_json() or {}
    get_scheduler().toggle_task(data.get("id", 0))
    return {"status": "toggled"}

# ══════════════════════════════════════════════════════════════════════════════
#  VOICES / TTS
# ══════════════════════════════════════════════════════════════════════════════
VOICE_MAP = {"siri": "Samantha", "jarvis": "Alex", "gentleman": "Tom", "hermes": "hermes"}
HERMES_VENV = Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python"
HERMES_VOICE = "en-US-AriaNeural"


def tts(text):
    if not cfg.get("speak_on", False):
        return
    if not text or text.startswith("Routing:"):
        return
    voice = VOICE_MAP.get(cfg.get("voice_index", "siri"), "Samantha")
    try:
        if voice == "hermes":
            _tts_hermes(text)
        else:
            subprocess.Popen(["say", "-v", voice, text])
    except Exception:
        pass


def _tts_hermes(text):
    """Speak with the Hermes agent's built-in voice (edge-tts en-US-AriaNeural)."""
    if not HERMES_VENV.exists():
        subprocess.Popen(["say", "-v", "Samantha", text])
        return
    text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    payload = json.dumps(text, ensure_ascii=False)
    code = (
        "import asyncio, edge_tts, tempfile, subprocess, json\n"
        "async def main():\n"
        "    text = json.loads(" + json.dumps(payload) + ")\n"
        "    tts = edge_tts.Communicate(text, voice=" + json.dumps(HERMES_VOICE) + ")\n"
        "    p = tempfile.mktemp(suffix='.mp3')\n"
        "    await tts.save(p)\n"
        "    subprocess.Popen(['afplay', p])\n"
        "asyncio.run(main())\n"
    )
    subprocess.Popen([str(HERMES_VENV), "-c", code])


def push_message(text, sender="friday", emotion=None):
    """Send a message to the frontend conversation panel."""
    msg = {
        "id": str(uuid.uuid4())[:8],
        "sender": sender,
        "text": text,
        "time": datetime.now().strftime("%I:%M %p"),
        "emotion": emotion,
    }
    store.setdefault("conversation", []).append(msg)
    # Keep last 100 messages
    if len(store["conversation"]) > 100:
        store["conversation"] = store["conversation"][-100:]
    socketio.emit("conversation:message", msg)
    if sender == "friday":
        tts(text)
    try:
        if _chat_active and sender == "friday":
            _chat_collect.append(text)
    except Exception:
        pass
    return msg


# ══════════════════════════════════════════════════════════════════════════════
#  SPEECH RECOGNITION
# ══════════════════════════════════════════════════════════════════════════════
recognizer = sr.Recognizer() if VOICE_OK else None
voice_listening = False
voice_thread = None


def capture_audio(timeout=None, phrase_time_limit=4):
    with sr.Microphone() as source:
        if timeout:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        else:
            audio = recognizer.listen(source, phrase_time_limit=phrase_time_limit)
    return audio


def recognize_audio(audio):
    try:
        return recognizer.recognize_google(audio).lower()
    except Exception:
        return ""


def detect_double_clap(single_window=0.55, thresh=None):
    if thresh is None:
        thresh = cfg.get("clap_thresh", 2000)
    try:
        a1 = capture_audio(timeout=1, phrase_time_limit=single_window)
        rms1 = audioop.rms(a1.get_raw_data(convert_rate=16000, convert_width=2), 2)
        if rms1 < thresh:
            return False
        a2 = capture_audio(timeout=1, phrase_time_limit=single_window)
        rms2 = audioop.rms(a2.get_raw_data(convert_rate=16000, convert_width=2), 2)
        return rms2 >= thresh
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  EMOTION DETECTION
# ══════════════════════════════════════════════════════════════════════════════
POS = ["khush", "happy", "achha", "good", "nice", "thanks", "shukriya"]
NEG = ["sad", "depressed", "tired", "thak", "gussa", "pareshan", "problem", "heart"]


def detect_emotion_text(text):
    s = sum(int(w in text) for w in POS) - sum(int(w in text) for w in NEG)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"


def detect_emotion_audio(audio):
    try:
        rms = audioop.rms(audio.get_raw_data(convert_rate=16000, convert_width=2), 2)
        if rms > 3500:
            return "strong"
    except Exception:
        pass
    return "neutral"


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND NORMALIZER
# ══════════════════════════════════════════════════════════════════════════════
def normalize_command(text):
    t = text.lower()
    t = t.replace("khol de", "open").replace("kholna", "open").replace("kholo", "open")
    t = t.replace("chala do", "open").replace("band ho ja", "stop").replace("band kar", "stop")
    t = t.replace("spotify chalo", "open spotify").replace("whatsapp app", "open whatsapp")
    t = re.sub(r"\bchrome\b", "open chrome", t)
    t = re.sub(r"\bbrave\b", "open brave", t)
    t = t.replace("chat gpt", "open chatgpt")
    t = t.replace("please", "").replace("pls", "").strip()
    return " ".join(t.split())


# ══════════════════════════════════════════════════════════════════════════════
#  BROWSER CONTROLLER (Playwright)
# ══════════════════════════════════════════════════════════════════════════════
class BrowserController:
    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None
        self._lock = threading.Lock()
        self.status = "OFF"

    def _emit_status(self, status):
        self.status = status
        socketio.emit("browser:status", {"status": status})

    def _ensure_browser(self):
        if self._browser and self._browser.is_connected():
            return True
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=False, slow_mo=50)
            ctx = self._browser.new_context()
            self._page = ctx.new_page()
            self._emit_status("READY")
            return True
        except Exception as e:
            print("[Browser] Launch error:", e)
            self._emit_status("ERROR")
            return False

    def open_browser(self):
        with self._lock:
            ok = self._ensure_browser()
            msg = "Browser opened and ready" if ok else "Failed to open browser"
            push_message(msg)

    def close_browser(self):
        with self._lock:
            try:
                if self._browser:
                    self._browser.close()
                if self._pw:
                    self._pw.stop()
            except Exception:
                pass
            self._browser = None
            self._page = None
            self._pw = None
            self._emit_status("OFF")
            push_message("Browser closed")

    def go_to(self, url):
        if not url.startswith("http"):
            url = "https://" + url

        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                self._emit_status("NAVIGATING")
                try:
                    self._page.goto(url, timeout=15000)
                    title = self._page.title()
                    self._emit_status("READY")
                    push_message(f"Opened: {title[:60]}")
                except Exception as e:
                    push_message("Navigation failed")
                    print("[Browser] go_to error:", e)

        threading.Thread(target=_run, daemon=True).start()

    def search_google(self, query):
        encoded = urllib.parse.quote_plus(query)
        self.go_to(f"https://www.google.com/search?q={encoded}")
        push_message(f"Searching Google for: {query}")

    def search_youtube(self, query):
        encoded = urllib.parse.quote_plus(query)
        self.go_to(f"https://www.youtube.com/results?search_query={encoded}")
        push_message(f"Searching YouTube for: {query}")

    def click_text(self, text):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    self._page.get_by_text(text, exact=False).first.click(timeout=5000)
                    push_message(f"Clicked: {text}")
                except Exception:
                    push_message(f"Could not click: {text}")

        threading.Thread(target=_run, daemon=True).start()

    def scroll(self, direction="down"):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    delta = 600 if direction == "down" else -600
                    self._page.mouse.wheel(0, delta)
                    push_message(f"Scrolled {direction}")
                except Exception:
                    pass

        threading.Thread(target=_run, daemon=True).start()

    def read_page(self):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    text = self._page.inner_text("body")
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    summary = " ".join(lines)[:400]
                    push_message(f"Page content: {summary}")
                except Exception:
                    push_message("Could not read page")

        threading.Thread(target=_run, daemon=True).start()

    def take_screenshot(self):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    path = APP_DIR / f"screenshot_{int(time.time())}.png"
                    self._page.screenshot(path=str(path))
                    push_message("Screenshot saved to PersonalAssistant folder")
                    subprocess.Popen(["open", str(APP_DIR)])
                except Exception:
                    push_message("Screenshot failed")

        threading.Thread(target=_run, daemon=True).start()

    def fill_field(self, label, value):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    self._page.get_by_label(label, exact=False).first.fill(value)
                    push_message(f"Filled {label} with {value}")
                except Exception:
                    push_message(f"Could not fill field: {label}")

        threading.Thread(target=_run, daemon=True).start()

    def go_back(self):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    self._page.go_back(timeout=8000)
                    push_message("Went back")
                except Exception:
                    push_message("Cannot go back")

        threading.Thread(target=_run, daemon=True).start()

    def go_forward(self):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    self._page.go_forward(timeout=8000)
                    push_message("Went forward")
                except Exception:
                    push_message("Cannot go forward")

        threading.Thread(target=_run, daemon=True).start()

    def refresh(self):
        def _run():
            with self._lock:
                if not self._ensure_browser():
                    return
                try:
                    self._page.reload(timeout=10000)
                    push_message("Page refreshed")
                except Exception:
                    push_message("Refresh failed")

        threading.Thread(target=_run, daemon=True).start()


browser = BrowserController() if PLAYWRIGHT_OK else None

# ══════════════════════════════════════════════════════════════════════════════
#  ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
def open_app(name, display_name=None):
    try:
        subprocess.Popen(["open", "-a", name])
        push_message(f"{display_name or name} opened")
    except Exception:
        push_message(f"Failed to open {display_name or name}")


def open_url(url):
    subprocess.Popen(["open", url])
    push_message(f"Opening {url}")


def set_volume(level):
    try:
        lvl = max(0, min(100, int(level)))
        subprocess.Popen(["osascript", "-e", f"set volume output volume {lvl}"])
        push_message(f"Volume set to {lvl}")
    except Exception:
        push_message("Volume command failed")


def set_timer_minutes(mins):
    def _t():
        try:
            m = int(mins)
            push_message(f"Timer set for {m} minutes")
            time.sleep(m * 60)
            push_message("⏰ Timer done!")
        except Exception:
            push_message("Timer error")

    threading.Thread(target=_t, daemon=True).start()


def translate_text(cmd):
    if not TRANSLATE_OK:
        push_message("Translation not available — install deep-translator")
        return
    try:
        parts = cmd.split("translate")[-1].strip().split("to")
        if len(parts) == 2:
            out = GoogleTranslator(source="auto", target=parts[1].strip()).translate(parts[0].strip())
            push_message(f"Translated: {out}")
        else:
            push_message("Use: translate <text> to <lang>")
    except Exception:
        push_message("Translation failed")


def learn_new_command(raw):
    try:
        payload = raw.split("learn command", 1)[1].strip() if "learn command" in raw else raw
        name, action = payload.split(":", 1)
        name = name.strip()
        action = action.strip()
        custom_cmds[name] = action
        store["custom_cmds"] = custom_cmds
        save_memory()
        push_message(f"Learned command: {name}")
    except Exception:
        push_message("Learning failed. Format: name: action")


def run_custom(name):
    action = custom_cmds.get(name)
    if not action:
        push_message("Command not found")
        return
    if action.startswith("open "):
        target = action.replace("open ", "").strip()
        if target.startswith("http"):
            open_url(target)
        else:
            open_app(target.title(), name)
    else:
        try:
            subprocess.Popen(action.split())
            push_message(f"Executed: {name}")
        except Exception:
            push_message("Execution failed")


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND PROCESSOR
# ══════════════════════════════════════════════════════════════════════════════
def process_command(cmd, audio_obj=None):
    normalized = normalize_command(cmd)
    em = detect_emotion_text(cmd)
    if audio_obj and VOICE_OK:
        em_s = detect_emotion_audio(audio_obj)
        if em_s != "neutral":
            em = "negative"

    # ── learning ──
    if "learn command" in normalized:
        learn_new_command(normalized)
        return
    if normalized in custom_cmds:
        run_custom(normalized)
        return

    # ── Smart Router (new: scenes, clipboard, system, file mgmt) ──
    routed = parse_command(cmd, clip_mgr)
    if routed:
        action = routed["action"]
        label = routed.get("label", "")
        if action == "run_scene":
            scene = routed["scene"]
            run_scene(scene)
            send_notification("FRIDAY Scene", f"Activated {scene} mode")
            push_message(label)
            return
        elif action == "tile_window":
            if routed["direction"] == "left":
                tile_window_left()
            else:
                tile_window_right()
            push_message(label)
            return
        elif action == "fullscreen":
            fullscreen_app()
            push_message(label)
            return
        elif action == "show_desktop":
            show_desktop()
            push_message(label)
            return
        elif action == "minimize_all":
            minimize_all()
            push_message(label)
            return
        elif action == "set_volume":
            set_volume(routed["level"])
            push_message(label)
            return
        elif action == "set_brightness":
            set_brightness(routed["level"])
            push_message(label)
            return
        elif action == "set_dark_mode":
            set_dark_mode(routed.get("enabled", True))
            push_message(label)
            return
        elif action == "lock_screen":
            lock_screen()
            push_message(label)
            return
        elif action == "sleep_display":
            sleep_display()
            push_message(label)
            return
        elif action == "empty_trash":
            empty_trash()
            push_message(label)
            return
        elif action == "clipboard_show":
            hist = clip_mgr.get_history(10)
            lines = "\n".join(f"• {e['text'][:60]}" for e in hist) if hist else "Nothing copied yet"
            push_message(f"📋 Clipboard History:\n{lines}")
            return
        elif action == "clipboard_clear":
            clip_mgr._load()
            clip_mgr.history["entries"] = []
            clip_mgr._save()
            push_message(label)
            return
        elif action == "save_snippet":
            clip_mgr.save_snippet(routed["name"], routed["text"])
            push_message(label)
            return
        elif action == "get_snippet":
            snippet = clip_mgr.get_snippet(routed["name"])
            if snippet:
                clip_mgr.copy_to_clipboard(snippet["text"])
                push_message(f"📋 Snippet '{routed['name']}': {snippet['text'][:100]}")
            else:
                push_message(f"❌ Snippet '{routed['name']}' not found")
            return
        elif action == "search_files":
            push_message(f"🔍 {label}")
            timer = threading.Timer(2.0, lambda: push_message(f"Found files matching '{routed['query']}' in downloads/coding/documents."))
            timer.start()
            return
        elif action == "open_folder":
            subprocess.Popen(["open", routed["path"]])
            push_message(label)
            return
        elif action == "open_app":
            mac_open_app(routed["app"])
            push_message(label)
            return
        elif action in ("greet", "acknowledge"):
            push_message(label)
            return
        elif action == "calendar_show":
            cal = get_calendar()
            events = cal.get_today_summary()
            if events:
                lines = "\n".join(f"• {e['title']} at {e['start_time'][:16]}" for e in events[:5])
                push_message(f"📅 Today's Schedule:\n{lines}")
            else:
                push_message("📅 No events today. Free day!")
            return
        elif action == "calendar_add":
            cal = get_calendar()
            parsed = cal.parse_natural(cmd)
            eid = cal.create_event(parsed["title"], parsed["start_time"], parsed["duration"])
            push_message(f"📅 Created: {parsed['title']} at {parsed['start_time'][:16]} ({parsed['duration']}min)")
            return
        elif action == "calendar_sync":
            cal = get_calendar()
            results = cal.full_sync()
            push_message(f"🔄 Calendar synced: {results['apple']} Apple, {results['google']} Google events imported")
            return
        elif action == "music_now":
            track = get_music().get_current_track()
            if track.get("playing"):
                push_message(f"🎵 **{track['title']}** — {track['artist']}\n💿 {track['album']}\n{track.get('album_art', '')}")
            else:
                push_message(track.get("title", "Nothing playing"))
            return
        elif action == "music_play":
            get_music().play()
            push_message("▶ Playing")
            return
        elif action == "music_pause":
            get_music().pause()
            push_message("⏸ Paused")
            return
        elif action == "music_next":
            get_music().next_track()
            push_message("⏭ Skipped")
            return
        elif action == "music_prev":
            get_music().previous_track()
            push_message("⏮ Previous")
            return
        elif action == "music_volume":
            lvl = get_music().set_volume(routed.get("level", 50))
            push_message(f"🔊 Volume {lvl}")
            return
        elif action == "music_open":
            get_music().open_music()
            push_message("🎵 Music opened")
            return
        elif action == "web_search":
            agent = get_web()
            results = agent.search_google(routed.get("query", ""))
            push_message(agent.format_results_for_chat(results))
            return
        elif action == "web_search_youtube":
            agent = get_web()
            results = agent.search_youtube(routed.get("query", ""))
            txt = f"📺 YouTube results for: {routed.get('query', '')}\n"
            for r in results.get("results", [])[:3]:
                txt += f"\n• {r.get('title', '')}\n  🔗 {r.get('link', '')}"
            push_message(txt)
            return
        elif action == "web_read":
            agent = get_web()
            result = agent.read_page(routed.get("url", ""))
            if "content" in result:
                push_message(f"📄 **{result.get('title', '')}**\n{result['content'][:1500]}")
            else:
                push_message(f"⚠️ {result.get('error', 'Read failed')}")
            return
        elif action == "vision_capture":
            agent = get_vision()
            result = agent.capture_screen()
            if "path" in result:
                push_message(f"📸 Screenshot captured ({result['size']//1024}KB)")
            else:
                push_message(f"⚠️ {result.get('error', 'Capture failed')}")
            return
        elif action == "vision_analyze":
            agent = get_vision()
            result = agent.capture_screen()
            if "path" in result:
                push_message("📸 Analyzing screen...")
                analysis = agent.analyze_with_llm(result["path"])
                push_message(f"👁 **Analysis:**\n{analysis}")
            else:
                push_message(f"⚠️ {result.get('error', 'Analysis failed')}")
            return
        elif action == "notes_list":
            notes = get_notes().all_notes()
            lines = []
            for src, items in notes.items():
                if items:
                    lines.append(f"\n**{src.title()}:**")
                    for n in items[:3]:
                        lines.append(f"• {n.get('title', '')[:50]}")
            push_message("📝 **Notes:**\n" + "\n".join(lines) if lines else "No notes yet")
            return
        elif action == "notes_create":
            get_notes().create_local_note(routed.get("title", "Note"), routed.get("body", ""))
            push_message(f"📝 Note saved: {routed.get('title', '')[:40]}")
            return
        elif action == "notes_apple":
            notes = get_notes().get_apple_notes()
            if notes:
                lines = "\n".join(f"• {n['title'][:50]}" for n in notes[:5])
                push_message(f"🍎 **Apple Notes:**\n{lines}")
            else:
                push_message("No Apple Notes found")
            return
        elif action == "email_list":
            from notes_engine import EmailEngine
            eng = EmailEngine()
            mail = eng.all_mail()
            lines = ["**Apple Mail:**"]
            for m in mail.get("apple", [])[:3]:
                lines.append(f"• {m.get('subject', '')[:40]} — {m.get('from', '')[:20]}")
            gmail = mail.get("gmail", [])
            if gmail:
                lines.append("\n**Gmail:**")
                for m in gmail[:3]:
                    lines.append(f"• {m.get('subject', '')[:40]} — {m.get('from', '')[:20]}")
            push_message("📬 **Email:**\n" + "\n".join(lines))
            return
        elif action == "git_status":
            result = get_git().status()
            push_message(f"📊 **Git Status:**\n{result.get('output', result.get('error', ''))[:500]}")
            return
        elif action == "git_log":
            result = get_git().log()
            push_message(f"📋 **Git Log:**\n{result.get('output', result.get('error', ''))[:500]}")
            return
        elif action == "git_run":
            git = get_git()
            cmd = routed.get("cmd", "")
            result = git.run(*shlex.split(cmd))
            if "pending" in result:
                push_message(f"🔐 {result['message']}")
            else:
                push_message(f"```\n{result.get('output', result.get('error', ''))[:500]}\n```")
            return
        elif action == "git_confirm":
            result = get_git().confirm_pending()
            push_message(f"```\n{result.get('output', result.get('error', ''))[:500]}\n```")
            return
        elif action == "memory_search":
            results = get_memory().search(routed.get("query", ""))
            if results:
                lines = "\n".join(f"• **{r['title']}** ({r['file']})" for r in results[:5])
                push_message(f"🧠 **Memory search:**\n{lines}")
            else:
                push_message("No relevant memories found")
            return
        elif action == "memory_save":
            path = get_memory().save_conversation(routed.get("user", ""), routed.get("friday", ""))
            push_message(f"🧠 Conversation saved to {path}")
            return
        elif action == "scheduler_list":
            tasks = get_scheduler().list_tasks()
            if tasks:
                lines = []
                for t in tasks[:10]:
                    status = "✅" if t.get("enabled") else "⏸"
                    lines.append(f"{status} **{t['name']}** ({t['trigger_type']}: {t['trigger_value']})")
                push_message("⏰ **Scheduled Tasks:**\n" + "\n".join(lines))
            else:
                push_message("No scheduled tasks")
            return
        # Fall through to old logic if no early return

    # ── BROWSER COMMANDS ──
    if browser:
        if normalized in ("open browser", "launch browser", "start browser"):
            browser.open_browser()
            return
        if normalized in ("close browser", "shut browser", "browser off"):
            browser.close_browser()
            return
        m = re.match(r"(?:search|google)\s+(?!youtube)(.+)", normalized)
        if m:
            browser.search_google(m.group(1).strip())
            return
        m = re.match(r"(?:search youtube|youtube search|youtube)\s+(.+)", normalized)
        if m:
            browser.search_youtube(m.group(1).strip())
            return
        m = re.match(r"(?:go to|browse to|navigate to|visit)\s+(.+)", normalized)
        if m:
            browser.go_to(m.group(1).strip())
            return
        m = re.match(r"click\s+(.+)", normalized)
        if m:
            browser.click_text(m.group(1).strip())
            return
        if "scroll down" in normalized:
            browser.scroll("down")
            return
        if "scroll up" in normalized:
            browser.scroll("up")
            return
        if normalized in ("read page", "read this page", "summarize page", "what does it say"):
            browser.read_page()
            return
        if "screenshot" in normalized:
            browser.take_screenshot()
            return
        m = re.match(r"fill\s+(.+?)\s+with\s+(.+)", normalized)
        if m:
            browser.fill_field(m.group(1).strip(), m.group(2).strip())
            return
        if normalized in ("go back", "back", "browser back"):
            browser.go_back()
            return
        if normalized in ("go forward", "forward", "browser forward"):
            browser.go_forward()
            return
        if normalized in ("refresh", "reload", "refresh page"):
            browser.refresh()
            return

    # ── APP / SYSTEM ──
    if "open chrome" in normalized:
        open_app("Google Chrome", "Chrome")
    elif "open brave" in normalized:
        open_app("Brave Browser", "Brave")
    elif "open whatsapp" in normalized:
        open_app("WhatsApp")
    elif "open spotify" in normalized:
        open_app("Spotify")
    elif "open chatgpt" in normalized:
        open_url("https://chat.openai.com")
        push_message("ChatGPT opened")
    elif "open terminal" in normalized:
        open_app("Terminal")
    elif "open notes" in normalized:
        open_app("Notes")
    elif "open " in normalized and "http" in normalized:
        open_url(normalized.split("open", 1)[1].strip())
    elif "translate" in normalized:
        translate_text(normalized)
    elif "timer" in normalized:
        m = re.search(r"(\d+)", normalized)
        if m:
            set_timer_minutes(m.group(1))
        else:
            push_message("Timer: specify minutes")
    elif "volume" in normalized:
        m = re.search(r"(\d+)", normalized)
        if m:
            set_volume(m.group(1))
        else:
            push_message("Specify volume 0-100")
    # ── config ──
    elif "voice jarvis" in normalized or "voice one" in normalized:
        cfg["voice_index"] = "jarvis"
        save_memory()
        push_message("Voice set to Jarvis")
    elif "voice siri" in normalized or "voice two" in normalized:
        cfg["voice_index"] = "siri"
        save_memory()
        push_message("Voice set to Siri")
    elif "voice gentleman" in normalized or "voice three" in normalized:
        cfg["voice_index"] = "gentleman"
        save_memory()
        push_message("Voice set to Gentleman")
    elif "voice hermes" in normalized or "voice four" in normalized or "hermes voice" in normalized:
        cfg["voice_index"] = "hermes"
        save_memory()
        push_message("Voice set to Hermes")
    elif "speak on" in normalized or "friday speak" in normalized:
        cfg["speak_on"] = True
        save_memory()
        push_message("Speech enabled")
        socketio.emit("config:state", cfg)
    elif "mute" in normalized or "speak off" in normalized or "friday mute" in normalized:
        cfg["speak_on"] = False
        save_memory()
        push_message("Speech disabled")
        socketio.emit("config:state", cfg)
    elif "enable clap" in normalized:
        cfg["clap_trigger"] = True
        save_memory()
        push_message("Clap trigger enabled")
        socketio.emit("config:state", cfg)
    elif "disable clap" in normalized:
        cfg["clap_trigger"] = False
        save_memory()
        push_message("Clap trigger disabled")
        socketio.emit("config:state", cfg)
    elif "enable continuous" in normalized:
        cfg["continuous_listen"] = True
        save_memory()
        push_message("Continuous listening enabled")
        socketio.emit("config:state", cfg)
    elif "disable continuous" in normalized:
        cfg["continuous_listen"] = False
        save_memory()
        push_message("Continuous listening disabled")
        socketio.emit("config:state", cfg)
    elif "stop" in normalized or "exit" in normalized or "band ho ja" in normalized:
        push_message("Shutting down Friday...")
    else:
        if normalized.startswith("open "):
            target = normalized.split("open ", 1)[1].strip()
            if target.startswith("http"):
                open_url(target)
            else:
                open_app(target.title(), target)
        else:
            # Forward to Multi-LLM Brain instead of saying 'Command not recognized'
            def callback(text):
                push_message(text, emotion=em)

            threading.Thread(target=process_with_brain, args=(cmd, callback), daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  SYSTEM MONITOR (background thread)
# ══════════════════════════════════════════════════════════════════════════════
def system_monitor_loop():
    """Emit system stats every 2 seconds."""
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            battery = psutil.sensors_battery()

            # Network check
            net_status = "Online"
            try:
                net_io = psutil.net_io_counters()
                if net_io.bytes_sent == 0 and net_io.bytes_recv == 0:
                    net_status = "Offline"
            except Exception:
                net_status = "Unknown"

            stats = {
                "cpu": round(cpu, 1),
                "mem_percent": round(mem.percent, 1),
                "mem_used": round(mem.used / (1024 ** 3), 1),
                "mem_total": round(mem.total / (1024 ** 3), 1),
                "disk_percent": round(disk.percent, 1),
                "disk_used": round(disk.used / (1024 ** 3), 1),
                "disk_total": round(disk.total / (1024 ** 3), 1),
                "battery": battery.percent if battery else None,
                "battery_plugged": battery.power_plugged if battery else None,
                "network": net_status,
                "uptime": int(time.time() - psutil.boot_time()),
            }

            # Health score: weighted average
            health = 100
            if cpu > 80:
                health -= (cpu - 80)
            if mem.percent > 85:
                health -= (mem.percent - 85) * 2
            if disk.percent > 90:
                health -= (disk.percent - 90) * 3
            stats["health"] = max(0, min(100, round(health)))

            # Bluetooth audio devices
            try:
                from mac_automation import get_bluetooth_devices
                stats["bluetooth"] = get_bluetooth_devices()
            except:
                stats["bluetooth"] = []

            socketio.emit("system:stats", stats)
        except Exception as e:
            print("[SysMon] Error:", e)
        time.sleep(2)


# ══════════════════════════════════════════════════════════════════════════════
#  VOICE LISTENER (background thread)
# ══════════════════════════════════════════════════════════════════════════════
def voice_listen_loop():
    """Background voice listening loop."""
    global voice_listening
    if not VOICE_OK:
        return

    push_message("Voice engine online. Say 'Friday' to activate.")
    socketio.emit("voice:status", {"state": "idle"})

    while voice_listening:
        triggered = False

        # Double clap detection
        if cfg.get("clap_trigger", False):
            try:
                if detect_double_clap():
                    triggered = True
            except Exception:
                pass

        # Continuous listening
        if not triggered and cfg.get("continuous_listen", False):
            try:
                socketio.emit("voice:status", {"state": "listening"})
                audio = capture_audio(timeout=1, phrase_time_limit=3)
                raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                rms = audioop.rms(raw, 2)
                socketio.emit("voice:waveform", {"rms": rms})
                text = recognize_audio(audio)
                if text:
                    push_message(text, sender="user")
                    socketio.emit("voice:status", {"state": "processing"})
                    process_command(text, audio_obj=audio)
                socketio.emit("voice:status", {"state": "listening"})
                continue
            except Exception:
                pass

        # Wake word detection
        if not triggered:
            try:
                audio = capture_audio(timeout=1, phrase_time_limit=2)
                raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                rms = audioop.rms(raw, 2)
                socketio.emit("voice:waveform", {"rms": min(rms, 5000)})
                text = recognize_audio(audio)
                if cfg["wake_word"] in text:
                    triggered = True
            except Exception:
                pass

        if triggered:
            push_message("Yes?")
            socketio.emit("voice:status", {"state": "listening"})
            try:
                audio_cmd = capture_audio(
                    timeout=cfg.get("listen_timeout", 4), phrase_time_limit=5
                )
                raw = audio_cmd.get_raw_data(convert_rate=16000, convert_width=2)
                rms = audioop.rms(raw, 2)
                socketio.emit("voice:waveform", {"rms": rms})
                cmd_text = recognize_audio(audio_cmd)
                if not cmd_text:
                    push_message("Didn't catch that")
                    socketio.emit("voice:status", {"state": "idle"})
                    continue
                push_message(cmd_text, sender="user")
                socketio.emit("voice:status", {"state": "processing"})
                process_command(cmd_text, audio_obj=audio_cmd)
            except Exception as e:
                print("[Voice] Error:", e)
                push_message("Voice error occurred")
            finally:
                socketio.emit("voice:status", {"state": "idle"})

        time.sleep(0.12)

    socketio.emit("voice:status", {"state": "off"})


# ══════════════════════════════════════════════════════════════════════════════
#  NOW PLAYING (Spotify via AppleScript)
# ══════════════════════════════════════════════════════════════════════════════
def get_now_playing():
    """Get current Spotify track via AppleScript."""
    try:
        script = '''
        tell application "System Events"
            if exists (process "Spotify") then
                tell application "Spotify"
                    if player state is playing then
                        return (name of current track) & " — " & (artist of current track)
                    else
                        return "Paused"
                    end if
                end tell
            else
                return ""
            end if
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  SOCKETIO EVENT HANDLERS
# ══════════════════════════════════════════════════════════════════════════════
@socketio.on("connect")
def handle_connect():
    print("[WS] Client connected")
    # Update knowledge from real filesystem
    update_knowledge_from_fs()
    # Send initial state from DB
    emit("config:state", cfg)
    emit("task:list", db.get_tasks())
    emit("agenda:list", db.get_agenda())
    emit("knowledge:data", store.get("knowledge", {}))
    emit("automation:list", store.get("automations", []))
    emit("productivity:data", {"today": db.get_productivity_data()})
    emit("conversation:history", store.get("conversation", [])[-50:])
    emit("browser:status", {"status": browser.status if browser else "UNAVAILABLE"})
    emit("files:data", get_structure())

    # Send welcome
    if not store.get("conversation"):
        push_message("Friday v4 online. All systems operational.")
        # Send macOS notification once
        send_notification("FRIDAY AI", "System is online and ready.")


@socketio.on("disconnect")
def handle_disconnect():
    print("[WS] Client disconnected")


@socketio.on("command:send")
def handle_command(data):
    cmd = data.get("text", "").strip()
    if not cmd:
        return
    push_message(cmd, sender="user")
    threading.Thread(target=process_command, args=(cmd,), daemon=True).start()


@socketio.on("voice:start")
def handle_voice_start():
    global voice_listening, voice_thread
    if not VOICE_OK:
        push_message("Voice not available — install speechrecognition + pyaudio")
        return
    if voice_listening:
        return
    voice_listening = True
    voice_thread = threading.Thread(target=voice_listen_loop, daemon=True)
    voice_thread.start()


@socketio.on("voice:stop")
def handle_voice_stop():
    global voice_listening
    voice_listening = False
    socketio.emit("voice:status", {"state": "off"})
    push_message("Voice listening stopped")


@socketio.on("browser:open")
def handle_browser_open():
    if browser:
        threading.Thread(target=browser.open_browser, daemon=True).start()
    else:
        push_message("Browser not available — install playwright")


@socketio.on("browser:close")
def handle_browser_close():
    if browser:
        threading.Thread(target=browser.close_browser, daemon=True).start()


@socketio.on("task:create")
def handle_task_create(data):
    tid = "t" + str(uuid.uuid4())[:6]
    db.add_task(tid, data.get("title", "New Task"), data.get("priority", "medium"), data.get("due", ""))
    emit("task:list", db.get_tasks(), broadcast=True)
    send_notification("FRIDAY AI", f"Task created: {data.get('title', 'New Task')}")

@socketio.on("task:update")
def handle_task_update(data):
    db.update_task(data.get("id"), data.get("status"), data.get("progress"))
    emit("task:list", db.get_tasks(), broadcast=True)

@socketio.on("task:delete")
def handle_task_delete(data):
    db.delete_task(data.get("id"))
    emit("task:list", db.get_tasks(), broadcast=True)

@socketio.on("agenda:delete")
def handle_agenda_delete(data):
    db.delete_agenda(data.get("id"))
    emit("agenda:list", db.get_agenda(), broadcast=True)


@socketio.on("agenda:create")
def handle_agenda_create(data):
    aid = "a" + str(uuid.uuid4())[:6]
    db.add_agenda(aid, data.get("time", ""), data.get("title", ""), data.get("duration", ""))
    emit("agenda:list", db.get_agenda(), broadcast=True)


@socketio.on("agenda:delete")
def handle_agenda_delete(data):
    aid = data.get("id")
    store["agenda"] = [a for a in store.get("agenda", []) if a["id"] != aid]
    save_memory()
    emit("agenda:list", store["agenda"], broadcast=True)


@socketio.on("automation:toggle")
def handle_automation_toggle(data):
    aid = data.get("id")
    for a in store.get("automations", []):
        if a["id"] == aid:
            a["enabled"] = not a["enabled"]
            break
    save_memory()
    emit("automation:list", store["automations"], broadcast=True)


@socketio.on("config:update")
def handle_config_update(data):
    for k, v in data.items():
        if k in cfg:
            cfg[k] = v
    store["cfg"] = cfg
    save_memory()
    emit("config:state", cfg, broadcast=True)


@socketio.on("shortcut:run")
def handle_shortcut(data):
    action = data.get("action", "")
    if action == "open_ide":
        open_app("Visual Studio Code", "VS Code")
    elif action == "open_notes":
        open_app("Notes")
    elif action == "open_browser":
        if browser:
            threading.Thread(target=browser.open_browser, daemon=True).start()
        else:
            open_app("Safari", "Browser")
    elif action == "open_terminal":
        open_app("Terminal")
    elif action == "start_timer":
        set_timer_minutes(25)  # Pomodoro default
    elif action == "lock_screen":
        subprocess.Popen(["pmset", "displaysleepnow"])
        push_message("Screen locked")
    elif action == "open_spotify":
        open_app("Spotify")
    elif action == "open_chatgpt":
        open_url("https://chat.openai.com")
    elif action == "open_downloads":
        subprocess.Popen(["open", str(HOME / "Downloads")])
        push_message("Opened Downloads")
    elif action == "open_coding":
        subprocess.Popen(["open", str(HOME / "Downloads" / "Coding")])
        push_message("Opened Coding")
    elif action == "open_documents":
        subprocess.Popen(["open", str(HOME / "Documents")])
        push_message("Opened Documents")
    elif action == "open_folder":
        folder = data.get("path", "")
        if folder:
            subprocess.Popen(["open", str(HOME / folder)])
            push_message(f"Opened {folder}")
    else:
        push_message(f"Unknown shortcut: {action}")


@socketio.on("now_playing:get")
def handle_now_playing(data=None):
    track = get_now_playing()
    emit("now_playing:data", {"track": track or "Nothing playing"})

# ── File System ──
@socketio.on("files:list")
def handle_files_list(data=None):
    structure = get_structure()
    emit("files:data", structure)

# ── Scenes ──
@socketio.on("scene:run")
def handle_scene_run(data):
    scene = data.get("scene", "")
    if scene in SCENES:
        run_scene(scene)
        send_notification("FRIDAY Scene", f"Activated {scene} mode")
        emit("scene:status", {"scene": scene, "status": "running"})
    else:
        emit("scene:status", {"scene": scene, "status": "unknown"})

@socketio.on("scenes:list")
def handle_scenes_list(data=None):
    scenes_list = [{"id": k, "name": v.get("label", k), "actions": len(v.get("actions", []))} for k, v in SCENES.items()]
    emit("scenes:data", scenes_list)

# ── Clipboard ──
@socketio.on("clipboard:history")
def handle_clipboard_history(data=None):
    history = clip_mgr.get_history()
    emit("clipboard:data", {"entries": history})

@socketio.on("clipboard:copy")
def handle_clipboard_copy(data):
    text = data.get("text", "")
    result = clip_mgr.copy_to_clipboard(text)
    if text:
        subprocess.run(["osascript", "-e", f'display notification "Copied: {text[:80]}..." with title "📋 FRIDAY Clipboard"'])

@socketio.on("clipboard:save_snippet")
def handle_clipboard_save_snippet(data):
    name = data.get("name", "")
    text = data.get("text", "")
    if name and text:
        clip_mgr.save_snippet(name, text)
        emit("clipboard:snippet_saved", {"name": name})

@socketio.on("clipboard:get_snippet")
def handle_clipboard_get_snippet(data):
    name = data.get("name", "")
    snippet = clip_mgr.get_snippet(name)
    if snippet:
        clip_mgr.copy_to_clipboard(snippet["text"])
        emit("clipboard:snippet", {"name": name, "text": snippet["text"][:200]})

@socketio.on("clipboard:list_snippets")
def handle_clipboard_list_snippets(data=None):
    names = clip_mgr.list_snippets()
    emit("clipboard:snippets_list", names)

@socketio.on("clipboard:delete_snippet")
def handle_clipboard_delete_snippet(data):
    name = data.get("name", "")
    if clip_mgr.delete_snippet(name):
        emit("clipboard:snippet_deleted", {"name": name})

# ── Proactive ──
@socketio.on("proactive:get")
def handle_proactive_get(data=None):
    if proactive:
        suggestions = proactive.get_suggestions()
        emit("proactive:data", {"suggestions": suggestions})

# ── Calendar ──
@socketio.on("calendar:events")
def handle_calendar_events(data=None):
    cal = get_calendar()
    days = data.get("days", 7) if data else 7
    events = cal.get_events(days=days)
    emit("calendar:events", {"events": events, "apple": cal.apple.available, "google": cal.google.available})

@socketio.on("calendar:create")
def handle_calendar_create(data):
    cal = get_calendar()
    eid = cal.create_event(
        data.get("title", "Event"),
        data.get("start_time", ""),
        data.get("duration", 30),
        data.get("location", ""),
        data.get("notes", ""),
    )
    emit("calendar:created", {"id": eid, "title": data.get("title", "")})
    send_notification("📅 Event", f"{data.get('title', 'Event')} created")

@socketio.on("calendar:delete")
def handle_calendar_delete(data):
    cal = get_calendar()
    cal.delete_event(data.get("id", ""))
    emit("calendar:deleted", {"id": data.get("id", "")})

@socketio.on("calendar:sync")
def handle_calendar_sync(data=None):
    cal = get_calendar()
    results = cal.full_sync()
    emit("calendar:synced", results)

@socketio.on("calendar:today")
def handle_calendar_today(data=None):
    cal = get_calendar()
    events = cal.get_today_summary()
    emit("calendar:today", {"events": events, "count": len(events)})

# ── Music SocketIO ──
@socketio.on("music:get")
def handle_music_get(data=None):
    track = get_music().get_current_track()
    emit("music:now", track)

@socketio.on("music:play")
def handle_music_play(data=None):
    get_music().play()
    emit("music:status", {"status": "playing"})

@socketio.on("music:pause")
def handle_music_pause(data=None):
    get_music().pause()
    emit("music:status", {"status": "paused"})

@socketio.on("music:next")
def handle_music_next(data=None):
    get_music().next_track()
    emit("music:status", {"status": "next"})

@socketio.on("music:prev")
def handle_music_prev(data=None):
    get_music().previous_track()
    emit("music:status", {"status": "previous"})

@socketio.on("music:volume")
def handle_music_volume(data):
    lvl = get_music().set_volume(data.get("level", 50))
    emit("music:volume", {"volume": lvl})

# ── Web Agent SocketIO ──
@socketio.on("web:search")
def handle_web_search(data):
    query = data.get("query", "")
    if query:
        agent = get_web()
        results = agent.search_google(query)
        emit("web:results", results)

@socketio.on("web:read")
def handle_web_read(data):
    url = data.get("url", "")
    if url:
        agent = get_web()
        result = agent.read_page(url)
        emit("web:page", result)

# ── Vision SocketIO ──
@socketio.on("vision:capture")
def handle_vision_capture(data=None):
    agent = get_vision()
    result = agent.capture_screen()
    emit("vision:captured", result)

@socketio.on("vision:analyze")
def handle_vision_analyze(data):
    agent = get_vision()
    prompt = data.get("prompt", "What do you see?") if data else "What do you see?"
    analysis = agent.analyze_with_llm(prompt=prompt)
    emit("vision:analysis", {"analysis": analysis})

# ── Notes SocketIO ──
@socketio.on("notes:list")
def handle_notes_list(data=None):
    notes = get_notes().all_notes()
    emit("notes:data", notes)

@socketio.on("notes:create")
def handle_notes_create(data):
    eid = get_notes().create_local_note(data.get("title", ""), data.get("body", ""), data.get("folder", ""))
    emit("notes:created", {"id": eid, "title": data.get("title", "")})
    send_notification("📝 Note", f"{data.get('title', 'Note')} saved")

@socketio.on("notes:create_apple")
def handle_notes_create_apple(data):
    get_notes().create_apple_note(data.get("title", ""), data.get("body", ""))
    emit("notes:created", {"source": "apple", "title": data.get("title", "")})

# ── Email SocketIO ──
@socketio.on("email:list")
def handle_email_list(data=None):
    from notes_engine import EmailEngine
    eng = EmailEngine()
    emit("email:data", eng.all_mail())

# ── Git SocketIO ──
@socketio.on("git:status")
def handle_git_status(data=None):
    emit("git:result", get_git().status())

@socketio.on("git:log")
def handle_git_log(data=None):
    emit("git:result", get_git().log())

@socketio.on("git:run")
def handle_git_run(data):
    cmd = data.get("command", "")
    if cmd:
        git = get_git()
        result = git.run(*shlex.split(cmd))
        emit("git:result", result)
        if "output" in result:
            push_message(f"```\n{result['output'][:500]}\n```")

@socketio.on("git:confirm")
def handle_git_confirm(data=None):
    result = get_git().confirm_pending()
    emit("git:result", result)

@socketio.on("git:cancel")
def handle_git_cancel(data=None):
    result = get_git().cancel_pending()
    emit("git:result", result)

# ── Memory SocketIO ──
@socketio.on("memory:search")
def handle_memory_search(data):
    query = data.get("query", "")
    results = get_memory().search(query)
    emit("memory:results", {"results": results})

@socketio.on("memory:notes")
def handle_memory_notes(data=None):
    notes = get_memory().list_notes()
    emit("memory:notes_list", {"notes": notes})

@socketio.on("memory:read")
def handle_memory_read(data):
    path = data.get("path", "")
    content = get_memory().read_note(path)
    emit("memory:content", {"path": path, "content": content})

# ── Scheduler SocketIO ──
@socketio.on("scheduler:list")
def handle_scheduler_list(data=None):
    tasks = get_scheduler().list_tasks()
    emit("scheduler:tasks", {"tasks": tasks})

@socketio.on("scheduler:create")
def handle_scheduler_create(data):
    tid = get_scheduler().add_task(
        data.get("name", "Task"), data.get("description", ""),
        data.get("trigger_type", "interval"), data.get("trigger_value", "30m"),
        data.get("action_type", "notify"), data.get("action_config", {}))
    emit("scheduler:created", {"id": tid, "name": data.get("name", "")})
    send_notification("⏰ Scheduler", f"Task '{data.get('name', '')}' created")

@socketio.on("scheduler:delete")
def handle_scheduler_delete(data):
    get_scheduler().delete_task(data.get("id", 0))
    emit("scheduler:deleted", {"id": data.get("id", 0)})

@socketio.on("scheduler:toggle")
def handle_scheduler_toggle(data):
    get_scheduler().toggle_task(data.get("id", 0))
    emit("scheduler:toggled", {"id": data.get("id", 0)})

# ── System State ──
@socketio.on("system:state")
def handle_system_state(data=None):
    state = get_system_state()
    emit("system:state", state)

# ── macOS Notification ──
def send_notification(title, subtitle):
    try:
        subprocess.Popen(["osascript", "-e",
            f'display notification "{subtitle}" with title "{title}" sound name "default"'])
    except Exception:
        pass

# ── Update knowledge with real counts on connect ──
def update_knowledge_from_fs():
    counts = get_file_counts()
    for key, val in counts.items():
        store["knowledge"][key] = val
    save_memory()

@socketio.on("knowledge:search")
def handle_knowledge_search(data):
    query = data.get("query", "").lower()
    # Powerful internal search logic
    full_data = db.get_knowledge()
    if not query:
        emit("knowledge:data", full_data)
        return
    
    filtered = {k: v for k, v in full_data.items() if query in k or query in v['label'].lower()}
    emit("knowledge:data", filtered)


# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════════════════════
def context_callback(name, duration, is_new=False):
    """Callback for context updates."""
    if is_new:
        socketio.emit("context:update", {"app": name})
    else:
        db.log_context(name, "", duration)
        socketio.emit("productivity:data", {"today": db.get_productivity_data()})

ctx_mgr = FridayContext(callback=context_callback)

def start_background_threads():
    """Start system monitor and other background tasks."""
    t1 = threading.Thread(target=system_monitor_loop, daemon=True)
    t1.start()

    ctx_mgr.start()

    update_knowledge_from_fs()

    clip_mgr.start_monitoring(callback=lambda e: socketio.emit("clipboard:new_entry", e))

    def suggestion_handler(suggestion):
        socketio.emit("proactive:suggestion", suggestion)
    global proactive
    proactive = ProactiveEngine(suggestion_handler, scene_callback=lambda s: None, store=store)
    proactive.start()

    # Warm the OmniRoute gateway connection so first chat isn't cold
    def _warm_omniroute():
        try:
            import omniroute
            if omniroute.OMNIROUTE_KEY:
                requests.get(
                    f"{omniroute.OMNIROUTE_BASE}/models",
                    headers={"Authorization": f"Bearer {omniroute.OMNIROUTE_KEY}"},
                    timeout=5,
                )
        except Exception:
            pass
    threading.Thread(target=_warm_omniroute, daemon=True).start()

    # Start scheduler engine
    get_scheduler()

    # Launch push-to-talk hotkey helper (Right Option + Space) if not already running
    try:
        ptt_bin = Path(__file__).parent / "ptt_hotkey"
        import os as _os
        already = any("ptt_hotkey" in (p or "") for p in (_os.popen("pgrep -fl ptt_hotkey").read() or "").splitlines())
        if ptt_bin.exists() and not already:
            subprocess.Popen([str(ptt_bin)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print("[PTT] launch error:", e)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  FRIDAY AI — JARVIS-Style HUD Dashboard")
    print("  Starting on http://localhost:5050")
    print("=" * 60 + "\n")

    start_background_threads()

    socketio.run(app, host="0.0.0.0", port=5050, debug=False)


    