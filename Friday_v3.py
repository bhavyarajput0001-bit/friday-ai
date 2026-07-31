
# Friday_v3.py
# Upgraded: Full Browser Control via Playwright
# Search Google/YouTube, navigate URLs, click, scroll, read page, screenshot
# Theme A: Interact=light / Voice=dark neon | Pulse + Waveform | Threaded audio

import os, sys, json, threading, time, subprocess, re, audioop, queue, asyncio, urllib.parse
from pathlib import Path

# ── imports ────────────────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    from deep_translator import GoogleTranslator
    import tkinter as tk
    from tkinter import simpledialog, messagebox
except Exception as e:
    print("Missing libraries.\n pip3 install speechrecognition deep-translator pyaudio playwright")
    raise

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False
    print("[WARN] playwright not found — browser commands disabled")

# ── config & memory ────────────────────────────────────────────────────────────
HOME    = Path.home()
APP_DIR = HOME / "PersonalAssistant"
APP_DIR.mkdir(exist_ok=True)
MEM_FILE = APP_DIR / "friday_memory.json"

DEFAULT_CFG = {
    "mode": "interact",
    "voice_index": "siri",
    "speak_on": False,
    "clap_trigger": False,
    "wake_word": "friday",
    "clap_thresh": 2000,
    "listen_timeout": 4,
    "continuous_listen": False
}

if MEM_FILE.exists():
    try:
        data = json.load(open(MEM_FILE, "r"))
        cfg = data.get("cfg", DEFAULT_CFG.copy())
        custom_cmds = data.get("custom_cmds", {})
    except:
        cfg = DEFAULT_CFG.copy(); custom_cmds = {}
else:
    cfg = DEFAULT_CFG.copy(); custom_cmds = {}

def save_memory():
    json.dump({"cfg": cfg, "custom_cmds": custom_cmds}, open(MEM_FILE, "w"), indent=2)

# ── voices ─────────────────────────────────────────────────────────────────────
VOICE_MAP = {"siri": "Samantha", "jarvis": "Alex", "gentleman": "Tom"}
if cfg.get("voice_index") not in VOICE_MAP:
    cfg["voice_index"] = "siri"

def tts(text):
    if not cfg.get("speak_on", False): return
    voice = VOICE_MAP.get(cfg.get("voice_index", "siri"), "Samantha")
    try:
        subprocess.Popen(["say", "-v", voice, text])
    except: pass

# ── speech recognition ─────────────────────────────────────────────────────────
r = sr.Recognizer()

def capture_audio(timeout=None, phrase_time_limit=4):
    with sr.Microphone() as source:
        if timeout:
            audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        else:
            audio = r.listen(source, phrase_time_limit=phrase_time_limit)
    return audio

def recognize_audio(audio):
    try:
        return r.recognize_google(audio).lower()
    except:
        return ""

# ── double clap ────────────────────────────────────────────────────────────────
def detect_double_clap(single_window=0.55, thresh=None):
    if thresh is None: thresh = cfg.get("clap_thresh", 2000)
    try:
        a1 = capture_audio(timeout=1, phrase_time_limit=single_window)
        rms1 = audioop.rms(a1.get_raw_data(convert_rate=16000, convert_width=2), 2)
        if rms1 < thresh: return False
        a2 = capture_audio(timeout=1, phrase_time_limit=single_window)
        rms2 = audioop.rms(a2.get_raw_data(convert_rate=16000, convert_width=2), 2)
        return rms2 >= thresh
    except:
        return False

# ── emotion ────────────────────────────────────────────────────────────────────
POS = ["khush","happy","achha","good","nice","thanks","shukriya"]
NEG = ["sad","depressed","tired","thak","gussa","pareshan","problem","heart"]

def detect_emotion_text(text):
    s = 0
    for w in POS: s += int(w in text)
    for w in NEG: s -= int(w in text)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"

def detect_emotion_audio(audio):
    try:
        rms = audioop.rms(audio.get_raw_data(convert_rate=16000, convert_width=2), 2)
        if rms > 3500: return "strong"
    except: pass
    return "neutral"

# ── normalizer ─────────────────────────────────────────────────────────────────
def normalize_command(text):
    t = text.lower()
    t = t.replace("khol de","open").replace("kholna","open").replace("kholo","open")
    t = t.replace("chala do","open").replace("band ho ja","stop").replace("band kar","stop")
    t = t.replace("spotify chalo","open spotify").replace("whatsapp app","open whatsapp")
    t = re.sub(r"\bchrome\b","open chrome",t)
    t = re.sub(r"\bbrave\b","open brave",t)
    t = t.replace("chat gpt","open chatgpt")
    t = t.replace("please","").replace("pls","").strip()
    return " ".join(t.split())

# ══════════════════════════════════════════════════════════════════════════════
#  BROWSER CONTROLLER  (Playwright — runs on its own thread with sync API)
# ══════════════════════════════════════════════════════════════════════════════
class BrowserController:
    """Persistent Chromium browser controlled synchronously in a daemon thread."""

    def __init__(self):
        self._pw       = None
        self._browser  = None
        self._page     = None
        self._lock     = threading.Lock()
        self.status    = "OFF"

    # ── lifecycle ──────────────────────────────────────────────────────
    def _ensure_browser(self):
        """Launch Chromium if not already open."""
        if self._browser and self._browser.is_connected():
            return True
        try:
            self._pw      = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=False, slow_mo=50)
            ctx           = self._browser.new_context()
            self._page    = ctx.new_page()
            self.status   = "READY"
            _gui_set_browser_status("READY")
            return True
        except Exception as e:
            print("[Browser] Launch error:", e)
            self.status = "ERROR"
            _gui_set_browser_status("ERROR")
            return False

    def open_browser(self):
        with self._lock:
            ok = self._ensure_browser()
            msg = "Browser opened and ready" if ok else "Failed to open browser"
            resp_print_say(msg)

    def close_browser(self):
        with self._lock:
            try:
                if self._browser: self._browser.close()
                if self._pw:      self._pw.stop()
            except: pass
            self._browser = None
            self._page    = None
            self._pw      = None
            self.status   = "OFF"
            _gui_set_browser_status("OFF")
            resp_print_say("Browser closed")

    # ── navigation ─────────────────────────────────────────────────────
    def go_to(self, url):
        if not url.startswith("http"):
            url = "https://" + url
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                _gui_set_browser_status("NAVIGATING")
                try:
                    self._page.goto(url, timeout=15000)
                    title = self._page.title()
                    self.status = "READY"
                    _gui_set_browser_status("READY")
                    resp_print_say(f"Opened: {title[:60]}")
                except Exception as e:
                    resp_print_say("Navigation failed")
                    print("[Browser] go_to error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def search_google(self, query):
        encoded = urllib.parse.quote_plus(query)
        self.go_to(f"https://www.google.com/search?q={encoded}")
        resp_print_say(f"Searching Google for: {query}")

    def search_youtube(self, query):
        encoded = urllib.parse.quote_plus(query)
        self.go_to(f"https://www.youtube.com/results?search_query={encoded}")
        resp_print_say(f"Searching YouTube for: {query}")

    # ── interaction ────────────────────────────────────────────────────
    def click_text(self, text):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    self._page.get_by_text(text, exact=False).first.click(timeout=5000)
                    resp_print_say(f"Clicked: {text}")
                except Exception as e:
                    resp_print_say(f"Could not click: {text}")
                    print("[Browser] click error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def scroll(self, direction="down"):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    delta = 600 if direction == "down" else -600
                    self._page.mouse.wheel(0, delta)
                    resp_print_say(f"Scrolled {direction}")
                except Exception as e:
                    print("[Browser] scroll error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def read_page(self):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    text = self._page.inner_text("body")
                    # clean whitespace
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    summary = " ".join(lines)[:400]
                    print("FRIDAY (page):", summary)
                    tts(summary)
                except Exception as e:
                    resp_print_say("Could not read page")
                    print("[Browser] read_page error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def take_screenshot(self):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    path = APP_DIR / f"screenshot_{int(time.time())}.png"
                    self._page.screenshot(path=str(path))
                    resp_print_say(f"Screenshot saved to PersonalAssistant folder")
                    subprocess.Popen(["open", str(APP_DIR)])
                except Exception as e:
                    resp_print_say("Screenshot failed")
                    print("[Browser] screenshot error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def fill_field(self, label, value):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    self._page.get_by_label(label, exact=False).first.fill(value)
                    resp_print_say(f"Filled {label} with {value}")
                except Exception as e:
                    resp_print_say(f"Could not fill field: {label}")
                    print("[Browser] fill error:", e)
        threading.Thread(target=_run, daemon=True).start()

    def go_back(self):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    self._page.go_back(timeout=8000)
                    resp_print_say("Went back")
                except:
                    resp_print_say("Cannot go back")
        threading.Thread(target=_run, daemon=True).start()

    def go_forward(self):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    self._page.go_forward(timeout=8000)
                    resp_print_say("Went forward")
                except:
                    resp_print_say("Cannot go forward")
        threading.Thread(target=_run, daemon=True).start()

    def refresh(self):
        def _run():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    self._page.reload(timeout=10000)
                    resp_print_say("Page refreshed")
                except:
                    resp_print_say("Refresh failed")
        threading.Thread(target=_run, daemon=True).start()


# global browser instance
browser = BrowserController() if PLAYWRIGHT_OK else None

def _gui_set_browser_status(status):
    try:
        if gui:
            gui.browser_status_var.set(f"Browser: {status}")
    except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  ACTIONS  (apps, volume, timer, translate)
# ══════════════════════════════════════════════════════════════════════════════
def resp_print_say(msg, emotion=None):
    if cfg["mode"] == "voice":
        out = msg.split(".")[0] if len(msg) > 100 else msg
    else:
        out = f"{msg}. Focus. Solution first." if emotion == "negative" else msg
    print("FRIDAY:", out)
    tts(out)

def open_chrome():    subprocess.Popen(["open","-a","Google Chrome"]); resp_print_say("Chrome opened")
def open_brave():     subprocess.Popen(["open","-a","Brave Browser"]);  resp_print_say("Brave opened")
def open_whatsapp():  subprocess.Popen(["open","-a","WhatsApp"]);       resp_print_say("WhatsApp opened")
def open_spotify():   subprocess.Popen(["open","-a","Spotify"]);        resp_print_say("Spotify opened")
def open_chatgpt():   subprocess.Popen(["open","https://chat.openai.com"]); resp_print_say("ChatGPT opened")
def open_url(url):    subprocess.Popen(["open", url]);                  resp_print_say(f"Opening {url}")

def set_volume(level):
    try:
        lvl = max(0, min(100, int(level)))
        subprocess.Popen(["osascript","-e",f"set volume output volume {lvl}"])
        resp_print_say(f"Volume set to {lvl}")
    except:
        resp_print_say("Volume failed")

def set_timer_minutes(mins):
    def _t():
        try:
            m = int(mins); resp_print_say(f"Timer set for {m} minutes")
            time.sleep(m * 60); resp_print_say("Timer done!")
        except: resp_print_say("Timer error")
    threading.Thread(target=_t, daemon=True).start()

def translate_text(cmd):
    try:
        parts = cmd.split("translate")[-1].strip().split("to")
        if len(parts) == 2:
            out = GoogleTranslator(source='auto', target=parts[1].strip()).translate(parts[0].strip())
            resp_print_say("Translated: " + out)
        else:
            resp_print_say("Use: translate <text> to <lang>")
    except:
        resp_print_say("Translation failed")

# ── learning ──────────────────────────────────────────────────────────────────
def learn_new_command(raw):
    try:
        payload = raw.split("learn command",1)[1].strip() if "learn command" in raw else raw
        name, action = payload.split(":",1)
        name = name.strip(); action = action.strip()
        custom_cmds[name] = action; save_memory()
        resp_print_say(f"Learned: {name}")
    except:
        resp_print_say("Learning failed. Format: name: action")

def run_custom(name):
    action = custom_cmds.get(name)
    if not action: resp_print_say("Command not found"); return
    if action.startswith("open "):
        target = action.replace("open ","").strip()
        if target.startswith("http"): open_url(target)
        else:
            try: subprocess.Popen(["open","-a",target]); resp_print_say(f"Executed {name}")
            except: resp_print_say("Failed to open app")
    else:
        try: subprocess.Popen(action.split()); resp_print_say(f"Executed {name}")
        except: resp_print_say("Failed")

# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND PROCESSOR  (voice + text)
# ══════════════════════════════════════════════════════════════════════════════
def process_command(cmd, audio_obj=None):
    normalized = normalize_command(cmd)
    em = detect_emotion_text(cmd)
    if audio_obj:
        em_s = detect_emotion_audio(audio_obj)
        if em_s != "neutral": em = "negative"

    # ── learning ──────────────────────────────────────────────
    if "learn command" in normalized:
        learn_new_command(normalized); return
    if normalized in custom_cmds:
        run_custom(normalized); return

    # ── BROWSER COMMANDS ───────────────────────────────────────
    if browser:
        # open browser
        if normalized in ("open browser", "launch browser", "start browser"):
            browser.open_browser(); return

        # close browser
        if normalized in ("close browser", "shut browser", "browser off"):
            browser.close_browser(); return

        # google search: "search <query>" or "google <query>"
        m = re.match(r"(?:search|google)\s+(?!youtube)(.+)", normalized)
        if m:
            browser.search_google(m.group(1).strip()); return

        # youtube search: "search youtube <query>" / "youtube search <query>"
        m = re.match(r"(?:search youtube|youtube search|youtube)\s+(.+)", normalized)
        if m:
            browser.search_youtube(m.group(1).strip()); return

        # go to / open url: "go to github.com"
        m = re.match(r"(?:go to|browse to|navigate to|visit)\s+(.+)", normalized)
        if m:
            browser.go_to(m.group(1).strip()); return

        # click: "click Sign In"
        m = re.match(r"click\s+(.+)", normalized)
        if m:
            browser.click_text(m.group(1).strip()); return

        # scroll
        if "scroll down" in normalized or "scroll page down" in normalized:
            browser.scroll("down"); return
        if "scroll up" in normalized or "scroll page up" in normalized:
            browser.scroll("up"); return

        # read / summarize page
        if normalized in ("read page","read this page","summarize page","what does it say"):
            browser.read_page(); return

        # screenshot
        if "screenshot" in normalized or "take screenshot" in normalized:
            browser.take_screenshot(); return

        # fill field: "fill username with johnDoe"
        m = re.match(r"fill\s+(.+?)\s+with\s+(.+)", normalized)
        if m:
            browser.fill_field(m.group(1).strip(), m.group(2).strip()); return

        # navigation
        if normalized in ("go back","back","browser back"):
            browser.go_back(); return
        if normalized in ("go forward","forward","browser forward"):
            browser.go_forward(); return
        if normalized in ("refresh","reload","refresh page"):
            browser.refresh(); return

    # ── APP / SYSTEM COMMANDS ──────────────────────────────────
    if "open chrome"    in normalized: open_chrome()
    elif "open brave"   in normalized: open_brave()
    elif "open whatsapp"in normalized: open_whatsapp()
    elif "open spotify" in normalized: open_spotify()
    elif "open chatgpt" in normalized: open_chatgpt()
    elif "open " in normalized and "http" in normalized:
        open_url(normalized.split("open",1)[1].strip())
    elif "translate"    in normalized: translate_text(normalized)
    elif "timer"        in normalized:
        m = re.search(r"(\d+)", normalized)
        if m: set_timer_minutes(m.group(1))
        else: resp_print_say("Timer minutes not found")
    elif "volume"       in normalized:
        m = re.search(r"(\d+)", normalized)
        if m: set_volume(m.group(1))
        else: resp_print_say("Specify volume 0-100")
    # ── mode / config ──
    elif "switch to voice" in normalized or "voice mode" in normalized:
        cfg["mode"] = "voice"; save_memory(); gui.apply_theme(); resp_print_say("Voice mode on", em)
    elif "switch to interact" in normalized or "interact mode" in normalized:
        cfg["mode"] = "interact"; save_memory(); gui.apply_theme(); resp_print_say("Interact mode on", em)
    elif "voice jarvis"   in normalized or "voice one"   in normalized:
        cfg["voice_index"] = "jarvis"; save_memory(); resp_print_say("Jarvis voice")
    elif "voice siri"     in normalized or "voice two"   in normalized:
        cfg["voice_index"] = "siri"; save_memory(); resp_print_say("Siri voice")
    elif "voice gentleman" in normalized or "voice three" in normalized:
        cfg["voice_index"] = "gentleman"; save_memory(); resp_print_say("Gentleman voice")
    elif "speak on"        in normalized or "friday speak" in normalized:
        cfg["speak_on"] = True;  save_memory(); resp_print_say("Speech on")
    elif "mute" in normalized or "speak off" in normalized or "friday mute" in normalized:
        cfg["speak_on"] = False; save_memory(); resp_print_say("Speech off")
    elif "enable clap"    in normalized:
        cfg["clap_trigger"] = True;  save_memory(); resp_print_say("Clap enabled")
    elif "disable clap"   in normalized:
        cfg["clap_trigger"] = False; save_memory(); resp_print_say("Clap disabled")
    elif "enable continuous" in normalized:
        cfg["continuous_listen"] = True;  save_memory(); resp_print_say("Continuous listening on")
    elif "disable continuous" in normalized:
        cfg["continuous_listen"] = False; save_memory(); resp_print_say("Continuous listening off")
    elif "stop" in normalized or "exit" in normalized or "band ho ja" in normalized:
        resp_print_say("Shutting down"); raise SystemExit
    else:
        if normalized.startswith("open "):
            target = normalized.split("open ",1)[1].strip()
            if target.startswith("http"): open_url(target)
            else:
                try: subprocess.Popen(["open","-a", target.title()]); resp_print_say(f"Opening {target}")
                except: resp_print_say("Command not recognized")
        else:
            resp_print_say("Command not recognized", emotion=em)

# ══════════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════════
class FridayGUI:
    def __init__(self, root):
        self.root = root
        root.title("Friday v3 — AI Assistant")
        root.geometry("560x380")

        self.mode_label        = tk.StringVar()
        self.status_var        = tk.StringVar()
        self.browser_status_var= tk.StringVar()
        self.input_var         = tk.StringVar()
        self.mode_label.set(f"Mode: {cfg['mode']}")
        self.status_var.set(f"TTS: {'On' if cfg['speak_on'] else 'Off'} | Clap: {'On' if cfg['clap_trigger'] else 'Off'}")
        self.browser_status_var.set("Browser: OFF")

        # main frame
        self.top = tk.Frame(root)
        self.top.pack(fill="both", expand=True, padx=10, pady=8)

        # title
        self.title = tk.Label(self.top, text="FRIDAY v3", font=("Helvetica", 22, "bold"))
        self.title.pack()

        self.info = tk.Label(self.top, textvariable=self.mode_label, font=("Helvetica", 11))
        self.info.pack()

        self.browser_lbl = tk.Label(self.top, textvariable=self.browser_status_var,
                                    font=("Helvetica", 10, "italic"))
        self.browser_lbl.pack()

        # canvas — pulse circle + waveform
        self.canvas = tk.Canvas(self.top, width=340, height=90, highlightthickness=0)
        self.canvas.pack(pady=4)
        self.circle    = self.canvas.create_oval(145, 5, 195, 55, fill="", outline="#00aaff", width=3)
        self.wave_bars = [self.canvas.create_rectangle(10+i*22, 75, 20+i*22, 82, fill="#00aaff")
                          for i in range(14)]

        # text input for typed commands
        inp_frame = tk.Frame(self.top)
        inp_frame.pack(pady=4, fill="x")
        tk.Label(inp_frame, text="Command:", font=("Helvetica", 10)).pack(side="left", padx=4)
        self.entry = tk.Entry(inp_frame, textvariable=self.input_var, font=("Helvetica", 10), width=32)
        self.entry.pack(side="left", padx=4)
        tk.Button(inp_frame, text="Send", command=self._send_typed).pack(side="left", padx=4)
        root.bind("<Return>", lambda e: self._send_typed())

        # controls
        ctrl = tk.Frame(self.top)
        ctrl.pack(pady=6)
        tk.Button(ctrl, text="Start",      width=10, command=self.start).grid(row=0, column=0, padx=5)
        tk.Button(ctrl, text="Stop",       width=10, command=self.stop).grid(row=0, column=1, padx=5)
        tk.Button(ctrl, text="TTS On/Off", width=10, command=self.toggle_speak).grid(row=0, column=2, padx=5)
        tk.Button(ctrl, text="Clap On/Off",width=10, command=self.toggle_clap).grid(row=1, column=0, padx=5, pady=5)
        tk.Button(ctrl, text="Open Browser",width=10, command=self._open_browser).grid(row=1, column=1, padx=5, pady=5)
        tk.Button(ctrl, text="Close Browser",width=10, command=self._close_browser).grid(row=1, column=2, padx=5, pady=5)

        # learn / memory
        row3 = tk.Frame(self.top)
        row3.pack()
        tk.Button(row3, text="Learn Command",    command=self.manual_learn).pack(side="left", padx=6)
        tk.Button(row3, text="Open Memory Folder", command=self.open_memory_folder).pack(side="left", padx=6)

        # animation state
        self.animating   = False
        self.pulse_scale = 1.0
        self._running    = False

    def apply_theme(self):
        if cfg["mode"] == "interact":
            bg="white"; fg="#111"; accent="#1a73e8"; entry_bg="#f0f0f0"
        else:
            bg="#0b0f18"; fg="#cfecff"; accent="#00d1ff"; entry_bg="#1a2030"
        self.root.configure(bg=bg)
        self.top.configure(bg=bg)
        self.title.configure(bg=bg, fg=fg)
        self.info.configure(bg=bg, fg=fg)
        self.browser_lbl.configure(bg=bg, fg=accent)
        self.canvas.configure(bg=bg)
        self.entry.configure(bg=entry_bg, fg=fg, insertbackground=fg)
        for w in [w for w in self.root.winfo_children()]:
            try: w.configure(bg=bg)
            except: pass
        for bar in self.wave_bars:
            self.canvas.itemconfig(bar, fill=accent)
        self.canvas.itemconfig(self.circle, outline=accent)
        self.status_var.set(f"TTS: {'On' if cfg['speak_on'] else 'Off'} | Clap: {'On' if cfg['clap_trigger'] else 'Off'}")

    def _send_typed(self):
        cmd = self.input_var.get().strip()
        if cmd:
            self.input_var.set("")
            print("YOU:", cmd)
            threading.Thread(target=process_command, args=(cmd,), daemon=True).start()

    def _open_browser(self):
        if browser: threading.Thread(target=browser.open_browser, daemon=True).start()

    def _close_browser(self):
        if browser: threading.Thread(target=browser.close_browser, daemon=True).start()

    def start(self):
        if self._running:
            messagebox.showinfo("Friday","Already running"); return
        self._running = True
        self.thread = threading.Thread(target=main_loop, daemon=True)
        self.thread.start()
        self.apply_theme()

    def running(self): return self._running

    def stop(self):
        self._running = False
        resp_print_say("Stopping Friday")

    def toggle_speak(self):
        cfg["speak_on"] = not cfg.get("speak_on", False)
        save_memory(); self.apply_theme(); resp_print_say("Speech toggled")

    def toggle_clap(self):
        cfg["clap_trigger"] = not cfg.get("clap_trigger", False)
        save_memory(); self.apply_theme(); resp_print_say("Clap toggled")

    def manual_learn(self):
        raw = simpledialog.askstring("Learn command",
                                     "Format: name:action\nE.g. instagram:open https://instagram.com")
        if raw: learn_new_command(raw)

    def open_memory_folder(self):
        subprocess.Popen(["open", str(APP_DIR)])

    # ── visuals ─────────────────────────────────────────────────────
    def start_pulse(self):
        self.animating = True
        threading.Thread(target=self._pulse_loop, daemon=True).start()

    def stop_pulse(self):
        self.animating = False

    def _pulse_loop(self):
        while self.animating:
            for s in [1.0,1.15,1.3,1.15,1.0]:
                self.pulse_scale = s; self._draw_pulse(); time.sleep(0.06)
            if not self.animating: break

    def _draw_pulse(self):
        r_size = 30 * self.pulse_scale
        cx, cy = 170, 30
        self.canvas.coords(self.circle, cx-r_size, cy-r_size, cx+r_size, cy+r_size)

    def draw_waveform(self, rms):
        max_h = 50; base = min(max(5, int(rms/50)), max_h)
        for i, bar in enumerate(self.wave_bars):
            h = max(2, int(base * (0.5 + 0.5 * ((i%3)/3.0))))
            self.canvas.coords(bar, 10+i*22, 80-h, 20+i*22, 80)

# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO WORKER
# ══════════════════════════════════════════════════════════════════════════════
rms_shared = {"last": 0}

def audio_worker_listen_once(timeout=None, phrase_time_limit=4):
    try:
        audio = capture_audio(timeout=timeout, phrase_time_limit=phrase_time_limit)
        raw   = audio.get_raw_data(convert_rate=16000, convert_width=2)
        rms   = audioop.rms(raw, 2)
        text  = recognize_audio(audio)
        return audio, text, rms
    except:
        return None, "", 0

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP  (background audio thread)
# ══════════════════════════════════════════════════════════════════════════════
def main_loop():
    gui.start_pulse()
    resp_print_say("Friday v3 online. Browser ready on command.")
    while gui.running():
        triggered = False

        if cfg.get("clap_trigger", False):
            try:
                if detect_double_clap(): triggered = True
            except: pass

        if not triggered and cfg.get("continuous_listen", False):
            try:
                audio, text, rms = audio_worker_listen_once(timeout=1, phrase_time_limit=3)
                if text:
                    rms_shared["last"] = rms
                    gui.draw_waveform(rms)
                    process_command(text, audio_obj=audio)
                continue
            except: pass

        if not triggered:
            try:
                audio = capture_audio(timeout=1, phrase_time_limit=2)
                text  = recognize_audio(audio)
                if cfg["wake_word"] in text: triggered = True
            except: pass

        if triggered:
            gui.stop_pulse(); gui.start_pulse()
            resp_print_say("Yes?")
            try:
                audio_cmd, cmd_text, rms = audio_worker_listen_once(
                    timeout=cfg.get("listen_timeout",4), phrase_time_limit=5)
                if not cmd_text:
                    resp_print_say("Didn't catch that")
                    gui.draw_waveform(rms); continue
                rms_shared["last"] = rms
                gui.draw_waveform(rms)
                print("Command heard:", cmd_text)
                if "switch to text" in cmd_text or "switch to interact" in cmd_text:
                    cfg["mode"] = "interact"; save_memory(); gui.apply_theme()
                    resp_print_say("Switched to interact mode"); continue
                if "switch to voice" in cmd_text or "voice mode" in cmd_text:
                    cfg["mode"] = "voice"; save_memory(); gui.apply_theme()
                    resp_print_say("Switched to voice mode"); continue
                process_command(cmd_text, audio_obj=audio_cmd)
            except SystemExit:
                resp_print_say("Friday offline"); break
            except Exception as e:
                print("Error:", e); resp_print_say("Error occurred")
            finally:
                gui.stop_pulse(); gui.start_pulse()
        time.sleep(0.12)

# ══════════════════════════════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════════════════════════════
root = tk.Tk()
gui  = FridayGUI(root)
gui.apply_theme()

if not PLAYWRIGHT_OK:
    messagebox.showwarning("Friday","Playwright not installed — browser commands disabled.\n"
                           "Run: pip3 install playwright && playwright install chromium")

greet = ("Siri style voice ready." if cfg.get("voice_index") == "siri"
         else "Jarvis style online." if cfg.get("voice_index") == "jarvis"
         else "Gentleman mode active.")
resp_print_say(greet)

try:
    root.mainloop()
except KeyboardInterrupt:
    print("Interrupted")
finally:
    if browser: browser.close_browser()