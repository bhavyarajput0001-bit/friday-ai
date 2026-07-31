import re, shlex
from mac_automation import (
    open_app, open_url, open_folder, set_volume, set_brightness,
    set_dark_mode, lock_screen, sleep_display, sleep_mac, empty_trash,
    tile_window_left, tile_window_right, fullscreen_app, switch_to_app,
    SCENES, run_scene, get_frontmost_app, get_system_state, launch_coding_session,
    launch_research_session,
)
from file_manager import ORGANIZED_FOLDERS

def parse_command(text, clipboard_manager=None):
    """
    Smart command parser. Returns structured action or None if unrecognized.
    """
    t = text.lower().strip()

    # ── SCENES / MODES ──
    if any(p in t for p in ["coding mode", "code mode", "coding session", "start coding"]):
        return {"action": "run_scene", "scene": "coding", "label": "🎬 Activating Coding Mode"}

    if any(p in t for p in ["movie mode", "movie time", "start movie", "cinema mode"]):
        return {"action": "run_scene", "scene": "movie", "label": "🎬 Movie Mode engaged"}

    if any(p in t for p in ["focus mode", "focus time", "do not disturb", "dnd mode"]):
        return {"action": "run_scene", "scene": "focus", "label": "🎯 Focus Mode activated"}

    if any(p in t for p in ["meeting mode", "meeting time", "start meeting"]):
        return {"action": "run_scene", "scene": "meeting", "label": "📋 Meeting Mode"}

    if any(p in t for p in ["clean up", "cleanup", "clean my mac"]):
        return {"action": "run_scene", "scene": "cleanup", "label": "🧹 Cleaning up"}

    if any(p in t for p in ["morning", "good morning", "briefing"]):
        return {"action": "run_scene", "scene": "morning", "label": "☀️ Morning Briefing"}

    # ── WINDOW MANAGEMENT ──
    if re.search(r"(tile|split|snap)\s+(left|right)", t):
        direction = "left" if "left" in t else "right"
        return {"action": "tile_window", "direction": direction, "label": f"↔ Tiled {direction}"}

    if "fullscreen" in t or "full screen" in t:
        return {"action": "fullscreen", "label": "🖥 Fullscreen"}

    if "show desktop" in t:
        return {"action": "show_desktop", "label": "🖥 Desktop"}

    if "minimize" in t or "hide all" in t:
        return {"action": "minimize_all", "label": "🙈 Windows hidden"}

    # ── SYSTEM ──
    if re.search(r"volume\s*(\d+)", t):
        m = re.search(r"volume\s*(\d+)", t)
        return {"action": "set_volume", "level": int(m.group(1)), "label": f"🔊 Volume {m.group(1)}"}

    if re.search(r"(brightness|screen)\s*(\d+)", t):
        m = re.search(r"(brightness|screen)\s*(\d+)", t)
        return {"action": "set_brightness", "level": int(m.group(2)), "label": f"☀️ Brightness {m.group(2)}%"}

    if "dark mode" in t:
        return {"action": "set_dark_mode", "enabled": "on" in t or "enable" in t, "label": "🌙 Dark mode toggled"}

    if any(p in t for p in ["lock screen", "lock my mac"]):
        return {"action": "lock_screen", "label": "🔒 Screen locked"}

    if any(p in t for p in ["sleep", "go to sleep", "good night"]):
        return {"action": "sleep_display", "label": "💤 Good night"}

    if "empty trash" in t or "clean trash" in t:
        return {"action": "empty_trash", "label": "🗑 Trash emptied"}

    # ── CLIPBOARD ──
    if "clipboard" in t or "copy" in t:
        if "show" in t or "history" in t or "list" in t:
            return {"action": "clipboard_show", "label": "📋 Clipboard history"}
        if "clear" in t:
            return {"action": "clipboard_clear", "label": "📋 Clipboard cleared"}

    if re.match(r"save (snippet|clip)\s+(\S+)\s+(.+)", t):
        m = re.match(r"save (snippet|clip)\s+(\S+)\s+(.+)", t)
        return {"action": "save_snippet", "name": m.group(2), "text": m.group(3), "label": f"📋 Snippet '{m.group(2)}' saved"}

    if re.match(r"get (snippet|clip)\s+(\S+)", t):
        m = re.match(r"get (snippet|clip)\s+(\S+)", t)
        return {"action": "get_snippet", "name": m.group(2), "label": f"📋 Loading snippet '{m.group(2)}'"}

    # ── FILES ──
    if re.search(r"(find|search|locate)\s+(my\s+)?(.+)", t):
        m = re.search(r"(find|search|locate)\s+(my\s+)?(.+)", t)
        query = m.group(3)
        return {"action": "search_files", "query": query, "label": f"🔍 Searching: {query}"}

    if re.search(r"open (downloads|documents|desktop|coding)", t):
        m = re.search(r"open (downloads|documents|desktop|coding)", t)
        folder_map = {
            "downloads": ORGANIZED_FOLDERS.get("Downloads"),
            "documents": ORGANIZED_FOLDERS.get("Documents"),
            "coding": ORGANIZED_FOLDERS.get("Coding"),
        }
        folder = folder_map.get(m.group(1))
        if folder:
            return {"action": "open_folder", "path": str(folder), "label": f"📁 Opened {m.group(1).title()}"}

    # ── APPS (generic) ──
    app_patterns = [
        (r"(open|launch|start)\s+(.+?)(\s+app)?$", lambda m: m.group(2).strip()),
        (r"switch to\s+(.+)", lambda m: m.group(1).strip()),
    ]
    for pat, extract in app_patterns:
        m = re.search(pat, t)
        if m:
            app = extract(m).title()
            known_apps = {
                "chrome": "Google Chrome", "vs code": "Visual Studio Code",
                "vscode": "Visual Studio Code", "code": "Visual Studio Code",
                "terminal": "Terminal", "safari": "Safari", "finder": "Finder",
                "notes": "Notes", "calendar": "Calendar", "spotify": "Spotify",
                "whatsapp": "WhatsApp", "telegram": "Telegram", "brave": "Brave Browser",
                "photos": "Photos", "music": "Music", "facetime": "FaceTime",
                "messages": "Messages", "settings": "System Settings",
                "preferences": "System Settings",
            }
            resolved = known_apps.get(app.lower(), app)
            return {"action": "open_app", "app": resolved, "label": f"🚀 Opening {resolved}"}

    # ── CALENDAR ──
    if re.search(r"(what'?s|show|my|today'?s)\s*(schedule|calendar|events|plan|day)", t):
        return {"action": "calendar_show", "label": "📅 Loading your schedule..."}

    if re.search(r"(add|create|schedule)\s+(event|meeting|appointment|call)", t):
        return {"action": "calendar_add", "text": text, "label": "📅 Creating event..."}

    if "sync calendar" in t or "sync my calendar" in t:
        return {"action": "calendar_sync", "label": "🔄 Syncing calendar..."}

    # ── MUSIC ──
    if re.search(r"(what'?s|show|now)\s*(playing|music|track|song)", t):
        return {"action": "music_now", "label": "🎵 Checking what's playing..."}

    if re.search(r"(play|resume)\s*(music|song|track)?$", t) and "playlist" not in t:
        return {"action": "music_play", "label": "▶ Playing"}

    if "pause" in t or "stop music" in t:
        return {"action": "music_pause", "label": "⏸ Paused"}

    if "next" in t or "skip" in t:
        return {"action": "music_next", "label": "⏭ Skipped"}

    if "previous" in t or "back" in t or "prev" in t:
        return {"action": "music_prev", "label": "⏮ Previous"}

    if re.search(r"volume\s*(\d+)", t):
        m = re.search(r"volume\s*(\d+)", t)
        return {"action": "music_volume", "level": int(m.group(1)), "label": f"🔊 Volume {m.group(1)}"}

    if "open music" in t or "open spotify" in t or "launch music" in t:
        return {"action": "music_open", "label": "🎵 Opening music app..."}

    # ── WEB AGENT ──
    m = re.match(r"(?:search|google)\s+(?!youtube)(.+)", t)
    if m:
        return {"action": "web_search", "query": m.group(1).strip(), "label": f"🔍 Searching: {m.group(1).strip()[:60]}"}

    m = re.match(r"(?:search youtube|youtube search)\s+(.+)", t)
    if m:
        return {"action": "web_search_youtube", "query": m.group(1).strip(), "label": f"📺 Searching YouTube: {m.group(1).strip()[:60]}"}

    m = re.match(r"(?:read|summarize|open)\s+(https?://\S+)", t)
    if m:
        return {"action": "web_read", "url": m.group(1), "label": f"📄 Reading page..."}

    # ── VISION ──
    if re.search(r"(what'?s on my screen|screenshot|capture screen|look at screen)", t):
        return {"action": "vision_capture", "label": "📸 Capturing screen..."}

    if re.search(r"(analyze|describe|what do you see)\s*(screen|screenshot|this)", t):
        return {"action": "vision_analyze", "label": "👁 Analyzing screen..."}

    # ── GENERAL CHAT ──
    greetings = ["hi", "hello", "hey", "yo", "sup", "whats up", "good morning", "good evening"]
    if any(g in t for g in greetings):
        return {"action": "greet", "label": "👋 Hello! How can I assist you today?"}

    thanks = ["thank", "thanks", "thank you", "thx", "appreciate"]
    if any(g in t for g in thanks):
        return {"action": "acknowledge", "label": "😊 You're welcome!"}

    # ── NOTES ──
    if re.search(r"(show|list|my)\s+(notes|note)", t):
        return {"action": "notes_list", "label": "📝 Loading notes..."}

    if re.match(r"(save|create|add|make)\s+(a\s+)?note\s+(called\s+|titled\s+|named\s+)?(.+)", t):
        m = re.match(r"(save|create|add|make)\s+(a\s+)?note\s+(called\s+|titled\s+|named\s+)?(.+)", t)
        return {"action": "notes_create", "title": m.group(4)[:60], "body": m.group(4), "label": f"📝 Saving note..."}

    if re.search(r"(apple|mac)\s+notes", t):
        return {"action": "notes_apple", "label": "🍎 Fetching Apple Notes..."}

    # ── EMAIL ──
    if re.search(r"(check|show|list|my)\s+(email|mail|inbox)", t):
        return {"action": "email_list", "label": "📬 Checking email..."}

    # ── GIT ──
    if "git status" in t or "repo status" in t:
        return {"action": "git_status", "label": "📊 Checking git status..."}

    if "git log" in t or "repo log" in t or "git history" in t:
        return {"action": "git_log", "label": "📋 Git log..."}

    m = re.match(r"git\s+(.+)", t)
    if m:
        return {"action": "git_run", "cmd": m.group(1), "label": f"🔧 Running git {m.group(1)}..."}

    if t in ("yes", "confirm", "do it") and False:
        return {"action": "git_confirm", "label": "✅ Confirming..."}

    # ── MEMORY ──
    if re.search(r"(remember|recall|search|find)\s+(in\s+)?(memory|obsidian|vault|notes)", t):
        m = re.search(r"(remember|recall|search|find)\s+(in\s+)?(memory|obsidian|vault|notes)\s+(.+)", t)
        query = m.group(4) if m else ""
        if not query:
            m = re.search(r"(what|tell)\s+(me\s+)?about\s+(.+)", t)
            query = m.group(3) if m else t
        return {"action": "memory_search", "query": query, "label": f"🧠 Searching memory: {query[:40]}"}

    if re.search(r"(save|record|remember)\s+this", t):
        return {"action": "memory_save", "user": "", "friday": "", "label": "🧠 Saving to memory..."}

    if re.search(r"(what do you know|what have we discussed|tell me about myself)", t):
        return {"action": "memory_search", "query": "personal preferences", "label": "🧠 Recalling..."}

    # ── SCHEDULER ──
    if re.search(r"(scheduled|automation|cron|background)\s+(tasks|jobs|items)", t):
        return {"action": "scheduler_list", "label": "⏰ Listing scheduled tasks..."}

    if re.search(r"(schedule|set up|create|add)\s+(a\s+)?(task|job|automation|cron)", t):
        from scheduler import SmartScheduler
        parsed = SmartScheduler().parse_natural(t)
        if parsed:
            return {"action": "scheduler_create", "trigger_type": parsed[0], "trigger_value": parsed[1], "label": f"⏰ Scheduling {parsed[0]} every {parsed[1]}..."}

    # Fallback: use LLM brain
    return None
