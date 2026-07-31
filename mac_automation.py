import subprocess, os, time, json, re
from pathlib import Path
from datetime import datetime
from threading import Thread

HOME = Path.home()

# ════════════════════════════════════════════════════════════════════
#  MAC SYSTEM CONTROL
# ════════════════════════════════════════════════════════════════════

def osascript(script):
    try:
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except: return ""

def open_app(app_name):
    subprocess.Popen(["open", "-a", app_name])

def open_url(url):
    subprocess.Popen(["open", url])

def open_folder(path):
    subprocess.Popen(["open", str(path)])

def set_volume(level):
    level = max(0, min(100, int(level)))
    osascript(f"set volume output volume {level}")

def get_volume():
    return osascript("output volume of (get volume settings)")

def set_brightness(level):
    level = max(0, min(100, int(level)))
    try:
        subprocess.run(["brightness", str(level / 100)], timeout=2)
    except:
        osascript(f"""
            tell application "System Events"
                repeat 100 times
                    key code 107
                end repeat
            end tell
        """)

def set_dark_mode(enabled):
    osascript(f"tell app \"System Events\" to tell appearance preferences to set dark mode to {'true' if enabled else 'false'}")

def toggle_do_not_disturb():
    osascript("""
        tell application "System Events"
            tell process "SystemUIServer"
                click (menu bar item 1 of menu bar 1 whose description contains "Notification")
            end tell
        end tell
    """)

def lock_screen():
    osascript("tell application \"System Events\" to keystroke \"q\" using {command down, control down}")

def sleep_display():
    subprocess.Popen(["pmset", "displaysleepnow"])

def sleep_mac():
    osascript("tell application \"Finder\" to sleep")

def empty_trash():
    osascript("tell application \"Finder\" to empty trash")

def get_frontmost_app():
    return osascript("tell application \"System Events\" to get name of first process whose frontmost is true")

def get_frontmost_window_title():
    return osascript("""
        tell application "System Events"
            tell (first process whose frontmost is true)
                tell (first window whose value of attribute "AXMain" is true)
                    return title
                end tell
            end tell
        end tell
    """)

# ════════════════════════════════════════════════════════════════════
#  WINDOW MANAGER
# ════════════════════════════════════════════════════════════════════

def tile_window_left(app_name=None):
    if app_name:
        osascript(f'tell application "{app_name}" to activate')
    time.sleep(0.2)
    osascript('tell application "System Events" to keystroke "a" using {option, command}')

def tile_window_right(app_name=None):
    if app_name:
        osascript(f'tell application "{app_name}" to activate')
    time.sleep(0.2)
    osascript('tell application "System Events" to keystroke "f" using {option, command}')

def fullscreen_app(app_name=None):
    if app_name:
        osascript(f'tell application "{app_name}" to activate')
    time.sleep(0.2)
    osascript('tell application "System Events" to keystroke "f" using {command, control}')

def minimize_all():
    osascript("""
        tell application "System Events"
            set visible of every process whose visible is true to false
        end tell
    """)

def show_desktop():
    osascript("""
        tell application "System Events"
            key code 103 using command down
        end tell
    """)

def switch_to_app(app_name):
    osascript(f'tell application "{app_name}" to activate')

# ════════════════════════════════════════════════════════════════════
#  SCENES (composable multi-action presets)
# ════════════════════════════════════════════════════════════════════

SCENES = {
    "coding": {
        "name": "Coding Mode",
        "icon": "💻",
        "description": "Open VS Code + Terminal + Browser",
        "actions": [
            {"type": "open_app", "params": {"name": "Visual Studio Code"}},
            {"type": "open_app", "params": {"name": "Terminal"}},
            {"type": "open_url", "params": {"url": "https://github.com"}},
        ]
    },
    "movie": {
        "name": "Movie Mode",
        "icon": "🎬",
        "description": "Dim lights, open Plex, fullscreen",
        "actions": [
            {"type": "set_brightness", "params": {"level": 30}},
            {"type": "set_volume", "params": {"level": 40}},
            {"type": "open_app", "params": {"name": "Plex"}},
        ]
    },
    "focus": {
        "name": "Focus Mode",
        "icon": "🎯",
        "description": "Block distractions, silence notifications",
        "actions": [
            {"type": "set_dark_mode", "params": {"enabled": True}},
            {"type": "open_app", "params": {"name": "Visual Studio Code"}},
            {"type": "set_volume", "params": {"level": 0}},
        ]
    },
    "meeting": {
        "name": "Meeting Mode",
        "icon": "📋",
        "description": "Silence Mac, open Calendar + Notes",
        "actions": [
            {"type": "set_volume", "params": {"level": 20}},
            {"type": "open_app", "params": {"name": "Calendar"}},
            {"type": "open_app", "params": {"name": "Notes"}},
        ]
    },
    "cleanup": {
        "name": "Clean Up",
        "icon": "🧹",
        "description": "Empty trash, close unused apps",
        "actions": [
            {"type": "empty_trash", "params": {}},
        ]
    },
    "morning": {
        "name": "Morning Briefing",
        "icon": "☀️",
        "description": "Open news, calendar, weather",
        "actions": [
            {"type": "set_brightness", "params": {"level": 70}},
            {"type": "open_url", "params": {"url": "https://news.google.com"}},
            {"type": "open_app", "params": {"name": "Calendar"}},
        ]
    },
}

def run_scene(scene_id, callback=None):
    scene = SCENES.get(scene_id)
    if not scene:
        if callback: callback(f"Scene '{scene_id}' not found")
        return False
    if callback: callback(f"🎬 Activating {scene['name']}...")
    for action in scene["actions"]:
        atype = action["type"]
        params = action["params"]
        try:
            if atype == "open_app":
                open_app(params["name"])
                if callback: callback(f"  → Opened {params['name']}")
            elif atype == "open_url":
                open_url(params["url"])
                if callback: callback(f"  → Opened URL")
            elif atype == "set_brightness":
                set_brightness(params["level"])
                if callback: callback(f"  → Brightness {params['level']}%")
            elif atype == "set_volume":
                set_volume(params["level"])
                if callback: callback(f"  → Volume {params['level']}%")
            elif atype == "set_dark_mode":
                set_dark_mode(params["enabled"])
                if callback: callback(f"  → Dark mode {'on' if params['enabled'] else 'off'}")
            elif atype == "empty_trash":
                empty_trash()
                if callback: callback("  → Trash emptied")
            time.sleep(0.5)
        except Exception as e:
            if callback: callback(f"  ✗ Error: {e}")
    if callback: callback(f"✅ {scene['name']} complete")
    return True

# ════════════════════════════════════════════════════════════════════
#  APP PROFILES (open app with specific files/context)
# ════════════════════════════════════════════════════════════════════

def launch_coding_session(project_path=None):
    open_app("Visual Studio Code")
    open_app("Terminal")
    if project_path:
        folder = HOME / project_path
        if folder.exists():
            open_folder(folder)

def launch_research_session(topic=None):
    open_app("Safari")
    if topic:
        import urllib.parse
        open_url(f"https://google.com/search?q={urllib.parse.quote_plus(topic)}")

# ════════════════════════════════════════════════════════════════════
#  SYSTEM STATE (for proactive engine)
# ════════════════════════════════════════════════════════════════════

def get_system_state():
    import psutil
    info = {}
    info["frontmost_app"] = get_frontmost_app()
    info["hour"] = datetime.now().hour
    info["day_name"] = datetime.now().strftime("%A")
    info["is_weekend"] = datetime.now().weekday() >= 5
    info["cpu"] = psutil.cpu_percent(interval=0.5)
    info["memory"] = psutil.virtual_memory().percent
    info["volume"] = get_volume()
    try:
        battery = psutil.sensors_battery()
        if battery:
            info["battery"] = battery.percent
            info["plugged"] = battery.power_plugged
    except:
        pass
    try:
        info["bluetooth"] = get_bluetooth_devices()
    except:
        info["bluetooth"] = []
    return info


def get_bluetooth_devices():
    """Return Bluetooth audio devices, connected and known-but-disconnected."""
    try:
        r = subprocess.run(["system_profiler", "SPBluetoothDataType", "-json"], capture_output=True, text=True, timeout=8)
        data = json.loads(r.stdout)
        devices = []
        bluetooth = data.get("SPBluetoothDataType", [])
        for item in bluetooth:
            for section in ("device_connected", "device_not_connected"):
                raw = item.get(section, {})
                connected = section == "device_connected"
                if isinstance(raw, list):
                    for entry in raw:
                        if isinstance(entry, dict):
                            for name, info in entry.items():
                                if isinstance(info, dict):
                                    _collect_audio_device(devices, name, info, connected)
                elif isinstance(raw, dict):
                    for name, info in raw.items():
                        if isinstance(info, dict):
                            _collect_audio_device(devices, name, info, connected)
        return devices
    except:
        return []


def _collect_audio_device(devices, name, info, connected):
    minor = info.get("device_minorType", "") or info.get("Minor Type", "")
    if minor in ("Headphones", "Speaker", "AirPods", "Beats", "Headset") or \
       "airpods" in name.lower() or "beats" in name.lower() or \
       "bud" in name.lower() or "earbud" in name.lower() or "headphone" in name.lower():
        devices.append({
            "name": name,
            "type": minor or "Audio",
            "connected": connected,
        })
