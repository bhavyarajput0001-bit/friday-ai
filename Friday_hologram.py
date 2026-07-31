
# Friday_hologram.py
# ═══════════════════════════════════════════════════════════════════════════════
#  FRIDAY  —  3D Golden Brain-Sphere Hologram
#  Inspired by glowing orbital neural sphere (JARVIS / Ultron style)
#  Full-screen on its own macOS Space
#  All v3 browser + voice + text capabilities
# ═══════════════════════════════════════════════════════════════════════════════

import os, sys, json, threading, time, subprocess, re, audioop, math, random, datetime
from pathlib import Path

try:
    import speech_recognition as sr
    from deep_translator import GoogleTranslator
    import tkinter as tk
    from tkinter import simpledialog, messagebox
except Exception as e:
    print("Missing: pip3 install speechrecognition deep-translator pyaudio"); raise

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

import urllib.parse

# ── palette — warm gold / amber / orange ───────────────────────────────────────
BG       = "#050505"
GOLD     = "#ffaa22"
AMBER    = "#ff8800"
ORANGE   = "#ff5500"
YELLOW   = "#ffcc44"
DIM_GOLD = "#664400"
DIM_ORG  = "#442200"
WHITE    = "#ffe8c8"
CORE_COL = "#ffdd66"
GLOW     = "#ffbb33"
CYAN     = "#00ccff"    # for text accents
GREEN    = "#44ff88"
GRID_COL = "#111100"

# generate a warm palette gradient (dim->bright for depth)
def _warm_color(brightness):
    """brightness 0.0 (far, dim) to 1.0 (near, bright)"""
    b = max(0.0, min(1.0, brightness))
    r = int(100 + 155 * b)
    g = int(40 + 120 * b * 0.7)
    bl = int(10 + 30 * b * 0.3)
    return f"#{r:02x}{g:02x}{bl:02x}"

# ── config & memory ────────────────────────────────────────────────────────────
HOME    = Path.home()
APP_DIR = HOME / "PersonalAssistant"
APP_DIR.mkdir(exist_ok=True)
MEM_FILE = APP_DIR / "friday_memory.json"

DEFAULT_CFG = {
    "mode": "interact", "voice_index": "jarvis", "speak_on": True,
    "clap_trigger": False, "wake_word": "friday", "clap_thresh": 2000,
    "listen_timeout": 5, "continuous_listen": False
}

if MEM_FILE.exists():
    try:
        data = json.load(open(MEM_FILE,"r"))
        cfg = data.get("cfg", DEFAULT_CFG.copy())
        custom_cmds = data.get("custom_cmds",{})
    except: cfg = DEFAULT_CFG.copy(); custom_cmds = {}
else: cfg = DEFAULT_CFG.copy(); custom_cmds = {}

def save_memory():
    json.dump({"cfg":cfg,"custom_cmds":custom_cmds}, open(MEM_FILE,"w"), indent=2)

VOICE_MAP = {"siri":"Samantha","jarvis":"Alex","gentleman":"Tom"}
if cfg.get("voice_index") not in VOICE_MAP: cfg["voice_index"] = "jarvis"

def tts(text):
    if not cfg.get("speak_on",False): return
    voice = VOICE_MAP.get(cfg.get("voice_index","jarvis"),"Alex")
    try: subprocess.Popen(["say","-v",voice,text])
    except: pass

r = sr.Recognizer()

def capture_audio(timeout=None, phrase_time_limit=4):
    with sr.Microphone() as source:
        if timeout: audio = r.listen(source,timeout=timeout,phrase_time_limit=phrase_time_limit)
        else: audio = r.listen(source,phrase_time_limit=phrase_time_limit)
    return audio

def recognize_audio(audio):
    try: return r.recognize_google(audio).lower()
    except: return ""

def detect_double_clap(single_window=0.55, thresh=None):
    if thresh is None: thresh = cfg.get("clap_thresh",2000)
    try:
        a1 = capture_audio(timeout=1,phrase_time_limit=single_window)
        rms1 = audioop.rms(a1.get_raw_data(convert_rate=16000,convert_width=2),2)
        if rms1 < thresh: return False
        a2 = capture_audio(timeout=1,phrase_time_limit=single_window)
        rms2 = audioop.rms(a2.get_raw_data(convert_rate=16000,convert_width=2),2)
        return rms2 >= thresh
    except: return False

POS = ["khush","happy","achha","good","nice","thanks","shukriya"]
NEG = ["sad","depressed","tired","thak","gussa","pareshan","problem","heart"]
def detect_emotion_text(text):
    s=0
    for w in POS: s+=int(w in text)
    for w in NEG: s-=int(w in text)
    return "positive" if s>0 else "negative" if s<0 else "neutral"
def detect_emotion_audio(audio):
    try:
        rms = audioop.rms(audio.get_raw_data(convert_rate=16000,convert_width=2),2)
        if rms>3500: return "strong"
    except: pass
    return "neutral"
def normalize_command(text):
    t=text.lower()
    t=t.replace("khol de","open").replace("kholna","open").replace("kholo","open")
    t=t.replace("chala do","open").replace("band ho ja","stop").replace("band kar","stop")
    t=t.replace("spotify chalo","open spotify").replace("whatsapp app","open whatsapp")
    t=re.sub(r"\bchrome\b","open chrome",t); t=re.sub(r"\bbrave\b","open brave",t)
    t=t.replace("chat gpt","open chatgpt").replace("please","").replace("pls","").strip()
    return " ".join(t.split())

# ══════════════════════════════════════════════════════════════════════════════
#  BROWSER CONTROLLER (same as v3)
# ══════════════════════════════════════════════════════════════════════════════
class BrowserController:
    def __init__(self):
        self._pw=None; self._browser=None; self._page=None
        self._lock=threading.Lock(); self.status="OFF"
    def _ensure_browser(self):
        if self._browser and self._browser.is_connected(): return True
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=False,slow_mo=50)
            ctx = self._browser.new_context(); self._page = ctx.new_page()
            self.status="READY"; _hud("browser","READY"); return True
        except Exception as e:
            print("[Browser]",e); self.status="ERROR"; _hud("browser","ERROR"); return False
    def open_browser(self):
        with self._lock:
            ok=self._ensure_browser(); resp("Browser opened" if ok else "Browser failed")
    def close_browser(self):
        with self._lock:
            try:
                if self._browser: self._browser.close()
                if self._pw: self._pw.stop()
            except: pass
            self._browser=self._page=self._pw=None; self.status="OFF"; _hud("browser","OFF"); resp("Browser closed")
    def _nav(self,url):
        if not url.startswith("http"): url="https://"+url
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                _hud("browser","NAV")
                try:
                    self._page.goto(url,timeout=15000); title=self._page.title()
                    self.status="READY"; _hud("browser","READY"); resp(f"Opened: {title[:50]}")
                except: resp("Navigation failed")
        threading.Thread(target=_r,daemon=True).start()
    def go_to(self,url): self._nav(url)
    def search_google(self,q): self._nav(f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"); resp(f"Searching: {q}")
    def search_youtube(self,q): self._nav(f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(q)}"); resp(f"YouTube: {q}")
    def click_text(self,text):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try: self._page.get_by_text(text,exact=False).first.click(timeout=5000); resp(f"Clicked: {text}")
                except: resp(f"Cannot click: {text}")
        threading.Thread(target=_r,daemon=True).start()
    def scroll(self,direction="down"):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try: self._page.mouse.wheel(0, 600 if direction=="down" else -600); resp(f"Scrolled {direction}")
                except: pass
        threading.Thread(target=_r,daemon=True).start()
    def read_page(self):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    text=self._page.inner_text("body"); lines=[l.strip() for l in text.splitlines() if l.strip()]
                    summary=" ".join(lines)[:400]; print("FRIDAY (page):",summary); tts(summary)
                except: resp("Cannot read page")
        threading.Thread(target=_r,daemon=True).start()
    def take_screenshot(self):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try:
                    p=APP_DIR/f"screenshot_{int(time.time())}.png"
                    self._page.screenshot(path=str(p)); resp("Screenshot saved"); subprocess.Popen(["open",str(APP_DIR)])
                except: resp("Screenshot failed")
        threading.Thread(target=_r,daemon=True).start()
    def fill_field(self,label,value):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try: self._page.get_by_label(label,exact=False).first.fill(value); resp(f"Filled {label}")
                except: resp(f"Cannot fill: {label}")
        threading.Thread(target=_r,daemon=True).start()
    def go_back(self):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try: self._page.go_back(timeout=8000); resp("Back")
                except: resp("Cannot go back")
        threading.Thread(target=_r,daemon=True).start()
    def go_forward(self):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try: self._page.go_forward(timeout=8000); resp("Forward")
                except: resp("Cannot go forward")
        threading.Thread(target=_r,daemon=True).start()
    def refresh(self):
        def _r():
            with self._lock:
                if not self._ensure_browser(): return
                try: self._page.reload(timeout=10000); resp("Refreshed")
                except: resp("Refresh failed")
        threading.Thread(target=_r,daemon=True).start()

browser = BrowserController() if PLAYWRIGHT_OK else None

def _hud(key, val):
    try:
        if hud: hud.set_status(key, val)
    except: pass

# ── actions (same as v3) ─────────────────────────────────────────────────────
def resp(msg, emotion=None):
    if cfg["mode"]=="voice": out=msg.split(".")[0] if len(msg)>100 else msg
    else: out=f"{msg}. Focus." if emotion=="negative" else msg
    print("FRIDAY:", out); tts(out)
    try:
        if hud: hud.push_log(out)
    except: pass

def open_chrome():   subprocess.Popen(["open","-a","Google Chrome"]); resp("Chrome opened")
def open_brave():    subprocess.Popen(["open","-a","Brave Browser"]);  resp("Brave opened")
def open_whatsapp(): subprocess.Popen(["open","-a","WhatsApp"]);       resp("WhatsApp opened")
def open_spotify():  subprocess.Popen(["open","-a","Spotify"]);        resp("Spotify opened")
def open_chatgpt():  subprocess.Popen(["open","https://chat.openai.com"]); resp("ChatGPT opened")
def open_url(url):   subprocess.Popen(["open",url]); resp(f"Opening {url}")
def set_volume(level):
    try: lvl=max(0,min(100,int(level))); subprocess.Popen(["osascript","-e",f"set volume output volume {lvl}"]); resp(f"Volume {lvl}")
    except: resp("Volume failed")
def set_timer_minutes(mins):
    def _t():
        try: m=int(mins); resp(f"Timer {m} min"); time.sleep(m*60); resp("Timer done!")
        except: resp("Timer error")
    threading.Thread(target=_t,daemon=True).start()
def translate_text(cmd):
    try:
        parts=cmd.split("translate")[-1].strip().split("to")
        if len(parts)==2: out=GoogleTranslator(source='auto',target=parts[1].strip()).translate(parts[0].strip()); resp("Translated: "+out)
        else: resp("Use: translate <text> to <lang>")
    except: resp("Translation failed")
def learn_new_command(raw):
    try:
        payload=raw.split("learn command",1)[1].strip() if "learn command" in raw else raw
        name,action=payload.split(":",1); name=name.strip(); action=action.strip()
        custom_cmds[name]=action; save_memory(); resp(f"Learned: {name}")
    except: resp("Learning failed. Format: name: action")
def run_custom(name):
    action=custom_cmds.get(name)
    if not action: resp("Not found"); return
    if action.startswith("open "):
        target=action.replace("open ","").strip()
        if target.startswith("http"): open_url(target)
        else:
            try: subprocess.Popen(["open","-a",target]); resp(f"Executed {name}")
            except: resp("Failed")
    else:
        try: subprocess.Popen(action.split()); resp(f"Executed {name}")
        except: resp("Failed")

# ── command processor ─────────────────────────────────────────────────────────
def process_command(cmd, audio_obj=None):
    normalized=normalize_command(cmd)
    em=detect_emotion_text(cmd)
    if audio_obj:
        if detect_emotion_audio(audio_obj)!="neutral": em="negative"
    if "learn command" in normalized: learn_new_command(normalized); return
    if normalized in custom_cmds: run_custom(normalized); return
    if browser:
        if normalized in ("open browser","launch browser","start browser"): browser.open_browser(); return
        if normalized in ("close browser","shut browser","browser off"): browser.close_browser(); return
        m=re.match(r"(?:search|google)\s+(?!youtube)(.+)",normalized)
        if m: browser.search_google(m.group(1).strip()); return
        m=re.match(r"(?:search youtube|youtube search|youtube)\s+(.+)",normalized)
        if m: browser.search_youtube(m.group(1).strip()); return
        m=re.match(r"(?:go to|browse to|navigate to|visit)\s+(.+)",normalized)
        if m: browser.go_to(m.group(1).strip()); return
        m=re.match(r"click\s+(.+)",normalized)
        if m: browser.click_text(m.group(1).strip()); return
        if "scroll down" in normalized: browser.scroll("down"); return
        if "scroll up" in normalized: browser.scroll("up"); return
        if normalized in ("read page","read this page","summarize page"): browser.read_page(); return
        if "screenshot" in normalized: browser.take_screenshot(); return
        m=re.match(r"fill\s+(.+?)\s+with\s+(.+)",normalized)
        if m: browser.fill_field(m.group(1).strip(),m.group(2).strip()); return
        if normalized in ("go back","back"): browser.go_back(); return
        if normalized in ("go forward","forward"): browser.go_forward(); return
        if normalized in ("refresh","reload"): browser.refresh(); return
    if "open chrome" in normalized: open_chrome()
    elif "open brave" in normalized: open_brave()
    elif "open whatsapp" in normalized: open_whatsapp()
    elif "open spotify" in normalized: open_spotify()
    elif "open chatgpt" in normalized: open_chatgpt()
    elif "open " in normalized and "http" in normalized: open_url(normalized.split("open",1)[1].strip())
    elif "translate" in normalized: translate_text(normalized)
    elif "timer" in normalized:
        m=re.search(r"(\d+)",normalized);
        if m: set_timer_minutes(m.group(1))
        else: resp("Timer minutes?")
    elif "volume" in normalized:
        m=re.search(r"(\d+)",normalized)
        if m: set_volume(m.group(1))
        else: resp("Volume 0-100?")
    elif "voice jarvis" in normalized: cfg["voice_index"]="jarvis"; save_memory(); resp("Jarvis voice")
    elif "voice siri" in normalized: cfg["voice_index"]="siri"; save_memory(); resp("Siri voice")
    elif "voice gentleman" in normalized: cfg["voice_index"]="gentleman"; save_memory(); resp("Gentleman voice")
    elif "speak on" in normalized: cfg["speak_on"]=True; save_memory(); resp("Speech on")
    elif "mute" in normalized or "speak off" in normalized: cfg["speak_on"]=False; save_memory(); resp("Speech off")
    elif "enable clap" in normalized: cfg["clap_trigger"]=True; save_memory(); resp("Clap on")
    elif "disable clap" in normalized: cfg["clap_trigger"]=False; save_memory(); resp("Clap off")
    elif "stop" in normalized or "exit" in normalized: resp("Shutting down"); raise SystemExit
    else:
        if normalized.startswith("open "):
            target=normalized.split("open ",1)[1].strip()
            if target.startswith("http"): open_url(target)
            else:
                try: subprocess.Popen(["open","-a",target.title()]); resp(f"Opening {target}")
                except: resp("Not recognized")
        else: resp("Not recognized",emotion=em)

# ══════════════════════════════════════════════════════════════════════════════
#   3D BRAIN SPHERE — Golden orbital arcs
# ══════════════════════════════════════════════════════════════════════════════

class OrbitalRing:
    """One orbital ring around the sphere — tilted, rotated in 3D."""
    def __init__(self, tilt_x, tilt_y, phase, arc_count, radius, speed):
        self.tilt_x   = tilt_x       # radians, tilt around X axis
        self.tilt_y   = tilt_y       # radians, tilt around Y axis
        self.phase    = phase        # initial rotation offset
        self.arc_count= arc_count    # how many arc segments to draw
        self.radius   = radius
        self.speed    = speed        # rotation speed (radians/tick)
        self.angle    = phase        # current rotation angle

    def get_points(self, cx, cy, n_points=60):
        """Return list of (screen_x, screen_y, depth_z) for this ring."""
        pts = []
        for i in range(n_points):
            theta = (2 * math.pi * i / n_points) + self.angle
            # 3D position on ring circle (in XZ plane)
            x = self.radius * math.cos(theta)
            y = 0
            z = self.radius * math.sin(theta)
            # rotate around X axis (tilt)
            y2 = y * math.cos(self.tilt_x) - z * math.sin(self.tilt_x)
            z2 = y * math.sin(self.tilt_x) + z * math.cos(self.tilt_x)
            # rotate around Y axis (tilt)
            x2 = x * math.cos(self.tilt_y) + z2 * math.sin(self.tilt_y)
            z3 = -x * math.sin(self.tilt_y) + z2 * math.cos(self.tilt_y)

            pts.append((cx + x2, cy + y2, z3))
        return pts


class BrainSphere:
    """The full brain-sphere: many orbital rings rendered as line segments."""
    def __init__(self, cx, cy, base_radius=220, ring_count=40):
        self.cx = cx
        self.cy = cy
        self.base_radius = base_radius
        self.rings = []
        self.spark_particles = []

        rng = random.Random(42)  # deterministic layout
        for i in range(ring_count):
            tilt_x = rng.uniform(0, math.pi)
            tilt_y = rng.uniform(0, math.pi)
            phase  = rng.uniform(0, 2*math.pi)
            arc_ct = rng.randint(2, 5)
            radius = base_radius + rng.uniform(-30, 30)
            speed  = rng.uniform(0.003, 0.02) * rng.choice([-1, 1])
            self.rings.append(OrbitalRing(tilt_x, tilt_y, phase, arc_ct, radius, speed))

        # inner detail rings (smaller, faster)
        for i in range(15):
            tilt_x = rng.uniform(0, math.pi)
            tilt_y = rng.uniform(0, math.pi)
            phase  = rng.uniform(0, 2*math.pi)
            radius = base_radius * rng.uniform(0.3, 0.7)
            speed  = rng.uniform(0.015, 0.04) * rng.choice([-1, 1])
            self.rings.append(OrbitalRing(tilt_x, tilt_y, phase, 3, radius, speed))

        # spark particles floating around the sphere
        for _ in range(80):
            angle1 = rng.uniform(0, 2*math.pi)
            angle2 = rng.uniform(0, math.pi)
            dist   = base_radius * rng.uniform(0.5, 1.3)
            self.spark_particles.append({
                "a1": angle1, "a2": angle2, "dist": dist,
                "speed1": rng.uniform(0.002, 0.012),
                "speed2": rng.uniform(0.001, 0.008),
                "size": rng.uniform(1, 3),
            })

    def update(self, rms_factor=1.0):
        """Step all rings forward."""
        for ring in self.rings:
            ring.angle += ring.speed * rms_factor
        for p in self.spark_particles:
            p["a1"] += p["speed1"]
            p["a2"] += p["speed2"] * 0.3

    def draw(self, cv, tag="sphere"):
        """Draw all rings as colored line segments onto canvas."""
        cv.delete(tag)
        cx, cy = self.cx, self.cy
        all_segs = []

        for ring in self.rings:
            pts = ring.get_points(cx, cy, n_points=48)
            # draw as connected line segments
            for j in range(len(pts)):
                p1 = pts[j]
                p2 = pts[(j+1) % len(pts)]
                # average depth for coloring
                avg_z = (p1[2] + p2[2]) / 2
                # normalized depth: -radius..+radius → 0..1
                depth = (avg_z + ring.radius) / (2 * ring.radius)
                depth = max(0.0, min(1.0, depth))
                all_segs.append((avg_z, p1, p2, depth, ring.radius))

        # sort by depth (back to front)
        all_segs.sort(key=lambda s: s[0])

        for avg_z, p1, p2, depth, rad in all_segs:
            # color based on depth: far=dim, near=bright gold
            brightness = 0.15 + 0.85 * depth
            color = _warm_color(brightness)
            # line width: thinner when far
            width = max(1, int(1 + 2 * depth))
            cv.create_line(p1[0], p1[1], p2[0], p2[1],
                           fill=color, width=width, tags=tag)

        # draw spark particles
        for p in self.spark_particles:
            x3 = p["dist"] * math.cos(p["a1"]) * math.sin(p["a2"])
            y3 = p["dist"] * math.cos(p["a2"])
            z3 = p["dist"] * math.sin(p["a1"]) * math.sin(p["a2"])
            depth = (z3 + self.base_radius) / (2 * self.base_radius)
            depth = max(0.0, min(1.0, depth))
            sx = cx + x3
            sy = cy + y3
            sz = p["size"] * (0.5 + depth)
            col = _warm_color(0.3 + 0.7 * depth)
            cv.create_oval(sx-sz, sy-sz, sx+sz, sy+sz,
                           fill=col, outline="", tags=tag)


# ══════════════════════════════════════════════════════════════════════════════
#  HOLOGRAM HUD
# ══════════════════════════════════════════════════════════════════════════════
class HologramHUD:
    TICK = 33  # ms per frame (~30 fps)

    def __init__(self, root):
        self.root = root
        root.title("FRIDAY")
        root.configure(bg=BG)
        root.attributes('-fullscreen', True)

        self.W = root.winfo_screenwidth()
        self.H = root.winfo_screenheight()
        self.cx = self.W // 2
        self.cy = self.H // 2 - 40  # shift sphere slightly up

        self.cv = tk.Canvas(root, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self.cv.pack(fill="both", expand=True)

        # state
        self._running   = False
        self._listening = False
        self._rms       = 0
        self._log_lines = []
        self._input_buf = ""
        self._status    = {
            "mode":"INTERACT","voice":"JARVIS","tts":"ON",
            "clap":"OFF","browser":"OFF","listen":"STANDBY"
        }
        self._tick = 0

        # create the brain sphere
        sphere_r = min(self.W, self.H) * 0.22
        self.brain = BrainSphere(self.cx, self.cy, base_radius=sphere_r, ring_count=35)

        # static elements
        self._draw_corner_brackets()
        self._build_ui_overlays()

        # key bindings
        root.bind("<KeyPress>", self._on_keypress)
        root.bind("<Escape>",   self._on_escape)
        root.bind("<F1>",       self._toggle_listen)
        root.bind("<F2>",       self._toggle_tts)
        root.bind("<F5>",       self._open_browser_key)

        # start animation
        self._animate()

    def _draw_corner_brackets(self):
        sz, gap, w = 50, 15, 2
        corners = [(gap,gap,1,1),(self.W-gap,gap,-1,1),
                   (gap,self.H-gap,1,-1),(self.W-gap,self.H-gap,-1,-1)]
        for (x,y,dx,dy) in corners:
            self.cv.create_line(x,y,x+dx*sz,y, fill=AMBER, width=w)
            self.cv.create_line(x,y,x,y+dy*sz, fill=AMBER, width=w)

    def _build_ui_overlays(self):
        cv = self.cv; cx = self.cx

        # title
        cv.create_text(cx, 45, text="F R I D A Y",
                       fill=GOLD, font=("Courier",32,"bold"))
        cv.create_text(cx, 75, text="NEURAL  INTELLIGENCE  SYSTEM",
                       fill=DIM_GOLD, font=("Courier",10))

        # status panel (right)
        sx = self.W - 250; sy = 130
        cv.create_rectangle(sx-10,sy-10,sx+225,sy+185,
                            outline=DIM_GOLD, fill="#0a0800", width=1)
        cv.create_text(sx+10,sy+5, text="─ SYSTEM STATUS ─",
                       fill=AMBER, font=("Courier",10,"bold"), anchor="w")
        self._status_texts = {}
        for i,(k,lbl) in enumerate([("mode","MODE"),("voice","VOICE"),("tts","TTS"),
                                     ("clap","CLAP"),("browser","BROWSER"),("listen","LISTEN")]):
            yy = sy+30+i*25
            cv.create_text(sx+10,yy, text=f"{lbl}:", fill=DIM_GOLD, font=("Courier",10), anchor="w")
            self._status_texts[k] = cv.create_text(sx+110,yy, text=self._status[k],
                                                    fill=GREEN, font=("Courier",10,"bold"), anchor="w")

        # log panel (left)
        lx=40; ly=130
        cv.create_rectangle(lx-10,ly-10,lx+310,ly+185,
                            outline=DIM_GOLD, fill="#0a0800", width=1)
        cv.create_text(lx+10,ly+5, text="─ OUTPUT LOG ─",
                       fill=AMBER, font=("Courier",10,"bold"), anchor="w")
        self._log_items = []
        for i in range(6):
            item = cv.create_text(lx+10,ly+30+i*25, text="",
                                  fill=WHITE, font=("Courier",10), anchor="w")
            self._log_items.append(item)

        # waveform (bottom center)
        self._wave_bars = []
        bar_n=36; bar_w=7; bar_gap=3
        total = bar_n*(bar_w+bar_gap)
        wx_start = cx - total//2
        wy = self.H - 110
        for i in range(bar_n):
            bx = wx_start + i*(bar_w+bar_gap)
            item = cv.create_rectangle(bx,wy-3,bx+bar_w,wy, fill=AMBER, outline="")
            self._wave_bars.append((bx,wy,bar_w,item))
        cv.create_text(cx, self.H-85, text="▲ AUDIO ▲", fill=DIM_GOLD, font=("Courier",9))

        # input bar
        iy = self.H - 55
        cv.create_rectangle(cx-370,iy-18,cx+370,iy+18,
                            outline=GOLD, fill="#0a0500", width=1)
        cv.create_text(cx-360,iy, text="❯", fill=GOLD, font=("Courier",14,"bold"), anchor="w")
        self._input_item = cv.create_text(cx-340,iy, text="", fill=WHITE,
                                           font=("Courier",13), anchor="w")
        self._cursor_blink = cv.create_text(cx-340,iy, text="█", fill=GOLD,
                                             font=("Courier",13), anchor="w")
        cv.create_text(cx, self.H-28,
                       text="F1: Voice   F2: TTS   F5: Browser   ESC: Exit",
                       fill=DIM_GOLD, font=("Courier",9))

        # time
        self._time_item = cv.create_text(cx, self.H-8, text="",
                                          fill=DIM_GOLD, font=("Courier",10))

    # ── animation loop ────────────────────────────────────────────────────
    def _animate(self):
        # update brain sphere — spin faster when listening / rms high
        rms_boost = 1.0 + (self._rms / 600.0) if self._listening else 0.6
        self.brain.update(rms_factor=rms_boost)
        self.brain.draw(self.cv, tag="sphere")

        # waveform
        t = self._tick * self.TICK / 1000.0
        base_h = max(3, int(self._rms / 50))
        for i,(bx,wy,bw,item) in enumerate(self._wave_bars):
            phase = math.sin(t*4 + i*0.35)
            h = max(2, int(base_h * (0.5 + 0.5*abs(phase)) +
                           random.uniform(0,1.5) * (1 if self._listening else 0.15)))
            h = min(h, 80)
            self.cv.coords(item, bx, wy-h, bx+bw, wy)
            col = GOLD if (self._listening and h>12) else AMBER if h>6 else DIM_GOLD
            self.cv.itemconfig(item, fill=col)

        # cursor blink
        if self._tick % 18 < 9:
            self.cv.itemconfig(self._cursor_blink, text="█")
        else:
            self.cv.itemconfig(self._cursor_blink, text=" ")
        cxp = self.cx - 340 + len(self._input_buf)*7.7
        self.cv.coords(self._cursor_blink, cxp, self.H-55)

        # time
        now = datetime.datetime.now().strftime("%H:%M:%S   %d %b %Y")
        self.cv.itemconfig(self._time_item, text=now)

        self._tick += 1
        self.root.after(self.TICK, self._animate)

    # ── public helpers ────────────────────────────────────────────────────
    def set_status(self, key, val):
        def _do():
            self._status[key] = str(val).upper()
            if key in self._status_texts:
                color = GREEN if val not in ("OFF","ERROR","STANDBY") else DIM_GOLD
                self.cv.itemconfig(self._status_texts[key], text=self._status[key], fill=color)
        self.root.after(0, _do)

    def push_log(self, msg):
        def _do():
            self._log_lines.append(msg)
            self._log_lines = self._log_lines[-6:]
            for i,item in enumerate(self._log_items):
                txt = self._log_lines[i] if i<len(self._log_lines) else ""
                self.cv.itemconfig(item, text=txt[:40])
        self.root.after(0, _do)

    def set_rms(self, rms): self._rms = rms
    def set_listening(self, val):
        self._listening = val
        self.set_status("listen", "ACTIVE" if val else "STANDBY")

    def running(self): return self._running
    def start_pulse(self): self.set_listening(True)
    def stop_pulse(self):  self.set_listening(False)
    def draw_waveform(self, rms): self.set_rms(rms)
    def apply_theme(self): pass

    def start(self):
        if self._running: return
        self._running = True
        threading.Thread(target=main_loop, daemon=True).start()
        self.push_log("Voice started. Say 'friday'.")

    def stop(self):
        self._running = False
        self.push_log("Listener stopped.")

    # ── keyboard ──────────────────────────────────────────────────────────
    def _on_keypress(self, event):
        if event.keysym == "BackSpace":
            self._input_buf = self._input_buf[:-1]
        elif event.keysym == "Return":
            cmd = self._input_buf.strip()
            self._input_buf = ""
            if cmd:
                self.push_log(f"> {cmd}")
                threading.Thread(target=process_command, args=(cmd,), daemon=True).start()
        elif event.char and event.char.isprintable():
            self._input_buf += event.char
        display = self._input_buf[-45:] if len(self._input_buf)>45 else self._input_buf
        self.cv.itemconfig(self._input_item, text=display)

    def _on_escape(self, event):
        if messagebox.askyesno("FRIDAY","Shut down FRIDAY?"):
            self.stop()
            if browser: browser.close_browser()
            self.root.destroy()

    def _toggle_listen(self, event=None):
        if not self._running: self.start()
        else: self.stop()

    def _toggle_tts(self, event=None):
        cfg["speak_on"] = not cfg.get("speak_on",False); save_memory()
        self.set_status("tts","ON" if cfg["speak_on"] else "OFF")
        resp("TTS "+("on" if cfg["speak_on"] else "off"))

    def _open_browser_key(self, event=None):
        if browser: threading.Thread(target=browser.open_browser, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO + MAIN LOOP
# ══════════════════════════════════════════════════════════════════════════════
rms_shared = {"last":0}

def audio_worker_listen_once(timeout=None, phrase_time_limit=5):
    try:
        audio = capture_audio(timeout=timeout,phrase_time_limit=phrase_time_limit)
        raw = audio.get_raw_data(convert_rate=16000,convert_width=2)
        rms = audioop.rms(raw,2); text = recognize_audio(audio)
        return audio, text, rms
    except: return None, "", 0

def main_loop():
    hud.set_listening(True)
    resp("FRIDAY online. All systems nominal.")
    while hud.running():
        triggered = False
        if cfg.get("clap_trigger",False):
            try:
                if detect_double_clap(): triggered = True
            except: pass
        if not triggered and cfg.get("continuous_listen",False):
            try:
                audio,text,rms = audio_worker_listen_once(timeout=1,phrase_time_limit=3)
                if text: rms_shared["last"]=rms; hud.set_rms(rms); process_command(text,audio_obj=audio)
                continue
            except: pass
        if not triggered:
            try:
                audio = capture_audio(timeout=1,phrase_time_limit=2)
                text = recognize_audio(audio)
                if cfg["wake_word"] in text: triggered=True
            except: pass
        if triggered:
            resp("Yes?")
            try:
                audio_cmd,cmd_text,rms = audio_worker_listen_once(
                    timeout=cfg.get("listen_timeout",5),phrase_time_limit=5)
                if not cmd_text: resp("Didn't catch that"); hud.set_rms(rms); continue
                rms_shared["last"]=rms; hud.set_rms(rms)
                print("Heard:", cmd_text)
                process_command(cmd_text,audio_obj=audio_cmd)
            except SystemExit: resp("FRIDAY offline"); break
            except Exception as e: print("Error:",e); resp("Error")
        time.sleep(0.10)
    hud.set_listening(False)

# ══════════════════════════════════════════════════════════════════════════════
#  LAUNCH
# ══════════════════════════════════════════════════════════════════════════════
root = tk.Tk()
hud  = HologramHUD(root)

if not PLAYWRIGHT_OK: hud.push_log("Playwright missing")
hud.push_log("FRIDAY — BRAIN SPHERE HOLOGRAM")
hud.push_log("F1: Voice | Type + Enter | ESC: Exit")
resp("FRIDAY hologram initialised.")

try: root.mainloop()
except KeyboardInterrupt: print("Interrupted")
finally:
    if browser: browser.close_browser()
