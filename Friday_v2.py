
# Friday_v2.py
# Upgraded: Theme A default (Interact light / Voice dark neon)
# Pulse (listening) + Waveform (based on RMS sample)
# Threaded audio, non-blocking TTS, UI theme switching, smoother timings

import os, sys, json, threading, time, subprocess, re, audioop, queue
from pathlib import Path

# imports
try:
    import speech_recognition as sr
    from deep_translator import GoogleTranslator
    import tkinter as tk
    from tkinter import simpledialog, messagebox
except Exception as e:
    print("Missing libraries. Run:\n brew install portaudio\n pip3 install speechrecognition deep-translator pyaudio")
    raise

# ---------- config & memory ----------
HOME = Path.home()
APP_DIR = HOME / "PersonalAssistant"
APP_DIR.mkdir(exist_ok=True)
MEM_FILE = APP_DIR / "friday_memory.json"

DEFAULT_CFG = {
    "mode": "interact",
    "voice_index": "siri",   # siri / jarvis / gentleman
    "speak_on": False,
    "clap_trigger": False,
    "wake_word": "friday",
    "clap_thresh": 2000,
    "listen_timeout": 4,
    "continuous_listen": False
}

if MEM_FILE.exists():
    try:
        data = json.load(open(MEM_FILE,"r"))
        cfg = data.get("cfg", DEFAULT_CFG.copy())
        custom_cmds = data.get("custom_cmds", {})
    except:
        cfg = DEFAULT_CFG.copy(); custom_cmds = {}
else:
    cfg = DEFAULT_CFG.copy(); custom_cmds = {}

def save_memory():
    json.dump({"cfg":cfg,"custom_cmds":custom_cmds}, open(MEM_FILE,"w"), indent=2)

# ---------- voices ----------
VOICE_MAP = {"siri":"Samantha", "jarvis":"Alex", "gentleman":"Tom"}
if cfg.get("voice_index") not in VOICE_MAP:
    cfg["voice_index"] = "siri"

def tts(text):
    if not cfg.get("speak_on", False): return
    voice = VOICE_MAP.get(cfg.get("voice_index","siri"), "Samantha")
    try:
        subprocess.Popen(["say", "-v", voice, text])
    except: pass

# ---------- audio & recognizer ----------
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

# ---------- double clap detection (lightweight) ----------
def detect_double_clap(single_window=0.55, thresh=None):
    if thresh is None: thresh = cfg.get("clap_thresh",2000)
    try:
        a1 = capture_audio(timeout=1, phrase_time_limit=single_window)
        rms1 = audioop.rms(a1.get_raw_data(convert_rate=16000, convert_width=2), 2)
        if rms1 < thresh: return False
        a2 = capture_audio(timeout=1, phrase_time_limit=single_window)
        rms2 = audioop.rms(a2.get_raw_data(convert_rate=16000, convert_width=2), 2)
        return rms2 >= thresh
    except: return False

# ---------- simple emotion ----------
POS = ["khush","happy","achha","good","nice","thanks","shukriya"]
NEG = ["sad","depressed","tired","thak","gussa","pareshan","problem","heart"]
def detect_emotion_text(text):
    s=0
    for w in POS: s+=int(w in text)
    for w in NEG: s-=int(w in text)
    return "positive" if s>0 else "negative" if s<0 else "neutral"

def detect_emotion_audio(audio):
    try:
        rms = audioop.rms(audio.get_raw_data(convert_rate=16000, convert_width=2),2)
        if rms > 3500: return "strong"
    except: pass
    return "neutral"

# ---------- normalizer (hinglish) ----------
def normalize_command(text):
    t = text.lower()
    t=t.replace("khol de","open").replace("kholna","open").replace("kholo","open")
    t=t.replace("chala do","open").replace("band ho ja","stop").replace("band kar","stop")
    t=t.replace("spotify chalo","open spotify").replace("whatsapp app","open whatsapp")
    t=re.sub(r"\bchrome\b","open chrome",t)
    t=re.sub(r"\bbrave\b","open brave",t)
    t=t.replace("chat gpt","open chatgpt")
    t=t.replace("please","").replace("pls","").strip()
    return " ".join(t.split())

# ---------- actions ----------
def resp_print_say(msg, emotion=None):
    if cfg["mode"]=="voice":
        out = msg.split(".")[0] if len(msg)>100 else msg
    else:
        if emotion=="negative": out = f"{msg}. Focus. Solution first."
        else: out = msg
    print("FRIDAY:", out)
    tts(out)

def open_chrome(): subprocess.Popen(["open","-a","Google Chrome"]); resp_print_say("Chrome opened")
def open_brave(): subprocess.Popen(["open","-a","Brave Browser"]); resp_print_say("Brave opened")
def open_whatsapp(): subprocess.Popen(["open","-a","WhatsApp"]); resp_print_say("WhatsApp opened")
def open_spotify(): subprocess.Popen(["open","-a","Spotify"]); resp_print_say("Spotify opened")
def open_chatgpt(): subprocess.Popen(["open","https://chat.openai.com"]); resp_print_say("ChatGPT opened")
def open_url(url): subprocess.Popen(["open", url]); resp_print_say(f"Opening {url}")
def set_volume(level):
    try:
        lvl = max(0, min(100, int(level)))
        subprocess.Popen(["osascript","-e",f"set volume output volume {lvl}"])
        resp_print_say(f"Volume set to {lvl}")
    except:
        resp_print_say("Volume failed")
def set_timer_minutes(mins):
    try:
        m=int(mins); resp_print_say(f"Timer set for {m} minutes"); time.sleep(m*60); resp_print_say("Timer finished")
    except: resp_print_say("Timer error")
def translate_text(cmd):
    try:
        parts = cmd.split("translate")[-1].strip().split("to")
        if len(parts)==2:
            text, lang = parts
            out = GoogleTranslator(source='auto', target=lang.strip()).translate(text.strip())
            resp_print_say("Translated: "+out)
        else:
            resp_print_say("Use: translate <text> to <lang>")
    except:
        resp_print_say("Translation failed")

# ---------- learning ----------
def learn_new_command(raw):
    try:
        payload = raw.split("learn command",1)[1].strip() if "learn command" in raw else raw
        name, action = payload.split(":",1)
        name=name.strip(); action=action.strip()
        custom_cmds[name]=action; save_memory(); resp_print_say(f"Learned {name}")
    except:
        resp_print_say("Learning failed. Use: name: action")

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
        except: resp_print_say("Failed to execute custom")

# ---------- process command ----------
def process_command(cmd, audio_obj=None):
    normalized = normalize_command(cmd)
    em = detect_emotion_text(cmd)
    if audio_obj:
        em_s = detect_emotion_audio(audio_obj)
        if em_s!="neutral": em="negative"
    if "learn command" in normalized: learn_new_command(normalized); return
    if normalized in custom_cmds: run_custom(normalized); return
    if "open chrome" in normalized: open_chrome()
    elif "open brave" in normalized: open_brave()
    elif "open whatsapp" in normalized: open_whatsapp()
    elif "open spotify" in normalized: open_spotify()
    elif "open chatgpt" in normalized: open_chatgpt()
    elif "open " in normalized and "http" in normalized: open_url(normalized.split("open",1)[1].strip())
    elif "translate" in normalized: translate_text(normalized)
    elif "timer" in normalized:
        m=re.search(r"(\d+)", normalized)
        if m: set_timer_minutes(m.group(1))
        else: resp_print_say("Timer minutes not found")
    elif "volume" in normalized:
        m=re.search(r"(\d+)", normalized)
        if m: set_volume(m.group(1))
        else: resp_print_say("Specify volume 0-100")
    elif "switch to voice" in normalized or "voice mode" in normalized:
        cfg["mode"]="voice"; save_memory(); gui.apply_theme(); resp_print_say("Voice mode on", em)
    elif "switch to interact" in normalized or "interact mode" in normalized:
        cfg["mode"]="interact"; save_memory(); gui.apply_theme(); resp_print_say("Interact mode on", em)
    elif "voice jarvis" in normalized or "voice one" in normalized:
        cfg["voice_index"]="jarvis"; save_memory(); resp_print_say("Jarvis voice selected")
    elif "voice siri" in normalized or "voice two" in normalized:
        cfg["voice_index"]="siri"; save_memory(); resp_print_say("Siri voice selected")
    elif "voice gentleman" in normalized or "voice three" in normalized:
        cfg["voice_index"]="gentleman"; save_memory(); resp_print_say("Gentleman voice selected")
    elif "speak on" in normalized or "friday speak" in normalized:
        cfg["speak_on"]=True; save_memory(); resp_print_say("Speech on")
    elif "mute" in normalized or "speak off" in normalized or "friday mute" in normalized:
        cfg["speak_on"]=False; save_memory(); resp_print_say("Speech off")
    elif "enable clap" in normalized:
        cfg["clap_trigger"]=True; save_memory(); resp_print_say("Clap enabled")
    elif "disable clap" in normalized:
        cfg["clap_trigger"]=False; save_memory(); resp_print_say("Clap disabled")
    elif "enable continuous" in normalized:
        cfg["continuous_listen"]=True; save_memory(); resp_print_say("Continuous listening enabled")
    elif "disable continuous" in normalized:
        cfg["continuous_listen"]=False; save_memory(); resp_print_say("Continuous listening disabled")
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

# ---------- UI (thread-safe) ----------
class FridayGUI:
    def __init__(self, root):
        self.root = root
        root.title("Friday — Personal Assistant")
        root.geometry("520x300")
        self.mode_label = tk.StringVar()
        self.status_var = tk.StringVar()
        self.mode_label.set(f"Mode: {cfg['mode']}")
        self.status_var.set(f"TTS: {'On' if cfg['speak_on'] else 'Off'} | Clap: {'On' if cfg['clap_trigger'] else 'Off'}")

        # main frame
        self.top = tk.Frame(root)
        self.top.pack(fill="both", expand=True, padx=10, pady=8)

        self.title = tk.Label(self.top, text="Friday", font=("Helvetica",20,"bold"))
        self.title.pack()

        self.info = tk.Label(self.top, textvariable=self.mode_label)
        self.info.pack()

        # canvas for visuals
        self.canvas = tk.Canvas(self.top, width=300, height=120, highlightthickness=0)
        self.canvas.pack(pady=6)
        # create pulse circle and bars
        self.circle = self.canvas.create_oval(120,10,180,70, fill="", outline="#00aaff", width=3)
        self.wave_bars = [ self.canvas.create_rectangle(10+i*20,90,20+i*20,100, fill="#00aaff") for i in range(12) ]

        # controls
        ctrl = tk.Frame(self.top)
        ctrl.pack(pady=6)
        tk.Button(ctrl, text="Start", width=10, command=self.start).grid(row=0,column=0,padx=6)
        tk.Button(ctrl, text="Stop", width=10, command=self.stop).grid(row=0,column=1,padx=6)
        tk.Button(ctrl, text="Voice", width=10, command=self.toggle_speak).grid(row=1,column=0,padx=6,pady=6)
        tk.Button(ctrl, text="Clap On/Off", width=10, command=self.toggle_clap).grid(row=1,column=1,padx=6,pady=6)
        tk.Button(self.top, text="Learn Command", command=self.manual_learn).pack(pady=4)
        tk.Button(self.top, text="Show Memory Folder", command=self.open_memory_folder).pack(pady=3)

        # theme related
        self.animating = False
        self.pulse_scale = 1.0
        self.wave_level = [2]*12

    def apply_theme(self):
        # Theme A: Interact = light, Voice = dark neon-blue
        if cfg["mode"]=="interact":
            bg="#f6f6f6"; fg="#111"; accent="#1a73e8"
        else:
            bg="#0b0f18"; fg="#cfecff"; accent="#00d1ff"
        self.root.configure(bg=bg)
        self.top.configure(bg=bg)
        self.title.configure(bg=bg, fg=fg)
        self.info.configure(bg=bg, fg=fg)
        self.status_var.set(f"TTS: {'On' if cfg['speak_on'] else 'Off'} | Clap: {'On' if cfg['clap_trigger'] else 'Off'}")
        # canvas colors
        for bar in self.wave_bars:
            self.canvas.itemconfig(bar, fill=accent)
        self.canvas.itemconfig(self.circle, outline=accent)

    def start(self):
        if self.running():
            messagebox.showinfo("Friday","Already running")
            return
        self._running = True
        self.thread = threading.Thread(target=main_loop, daemon=True)
        self.thread.start()
        self.apply_theme()

    def running(self):
        return getattr(self, "_running", False)

    def stop(self):
        self._running = False
        resp_print_say("Stopping Friday")

    def toggle_speak(self):
        cfg["speak_on"] = not cfg.get("speak_on", False); save_memory(); self.apply_theme(); resp_print_say("Speech toggled")

    def toggle_clap(self):
        cfg["clap_trigger"] = not cfg.get("clap_trigger", False); save_memory(); self.apply_theme(); resp_print_say("Clap toggled")

    def manual_learn(self):
        raw = simpledialog.askstring("Learn command", "Format: name:action\nE.g. instagram:open https://instagram.com")
        if raw: learn_new_command(raw)

    def open_memory_folder(self):
        subprocess.Popen(["open", str(APP_DIR)])

    # visual helpers
    def start_pulse(self):
        self.animating = True
        threading.Thread(target=self._pulse_loop, daemon=True).start()

    def stop_pulse(self):
        self.animating = False

    def _pulse_loop(self):
        while self.animating:
            # scale circle in/out
            for s in [1.0,1.15,1.3,1.15,1.0]:
                self.pulse_scale = s
                self._draw_pulse()
                time.sleep(0.06)
            if not self.animating: break

    def _draw_pulse(self):
        r = 30 * self.pulse_scale
        cx, cy = 150, 40
        x1, y1, x2, y2 = cx - r, cy - r, cx + r, cy + r
        self.canvas.coords(self.circle, x1, y1, x2, y2)

    def draw_waveform(self, rms):
        # rms 0..inf -> map to bar heights
        max_h = 60
        base = min(max(10, int(rms/50)), max_h)
        for i, bar in enumerate(self.wave_bars):
            # create small variance across bars
            h = max(2, int(base * (0.5 + 0.5 * ((i%3)/3.0))))
            self.canvas.coords(bar, 10+i*20, 100-h, 20+i*20, 100)

# ---------- main controller & queue ----------
command_queue = queue.Queue()
rms_shared = {"last": 0}

def audio_worker_listen_once(timeout=None, phrase_time_limit=4):
    """Capture audio, compute rms, return (audio, text, rms)"""
    try:
        audio = capture_audio(timeout=timeout, phrase_time_limit=phrase_time_limit)
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        rms = audioop.rms(raw, 2)
        text = recognize_audio(audio)
        return audio, text, rms
    except Exception:
        return None, "", 0

# ---------- main_loop (asynchronous, non-blocking UI) ----------
def main_loop():
    # runs on background thread
    gui.start_pulse()  # idle pulse while running to indicate readiness
    resp_print_say("Friday online.")
    while gui.running():
        triggered = False
        # check clap trigger
        if cfg.get("clap_trigger", False):
            # nonblocking quick check - if a double clap detected, proceed
            try:
                if detect_double_clap():
                    triggered = True
            except: pass

        # continuous listen mode
        if not triggered and cfg.get("continuous_listen", False):
            try:
                audio, text, rms = audio_worker_listen_once(timeout=1, phrase_time_limit=3)
                if text:
                    rms_shared["last"] = rms
                    gui.draw_waveform(rms)
                    process_command(text, audio_obj=audio)
                continue
            except: pass

        # quick wake-word sniff (low-latency short listen)
        if not triggered:
            try:
                audio = capture_audio(timeout=1, phrase_time_limit=2)
                text = recognize_audio(audio)
                if cfg["wake_word"] in text:
                    triggered = True
            except: pass

        if triggered:
            # stop idle pulse, start active pulse
            gui.stop_pulse()
            gui.start_pulse()
            resp_print_say("Yes?")
            try:
                audio_cmd, cmd_text, rms = audio_worker_listen_once(timeout=cfg.get("listen_timeout",4), phrase_time_limit=4)
                if not cmd_text:
                    resp_print_say("Didn't catch that")
                    gui.draw_waveform(rms)
                    continue
                rms_shared["last"] = rms
                gui.draw_waveform(rms)
                print("Command heard:", cmd_text)
                # direct switches
                if "switch to text" in cmd_text or "switch to interact" in cmd_text:
                    cfg["mode"] = "interact"; save_memory(); gui.apply_theme(); resp_print_say("Switched to interact mode"); continue
                if "switch to voice" in cmd_text or "voice mode" in cmd_text:
                    cfg["mode"] = "voice"; save_memory(); gui.apply_theme(); resp_print_say("Switched to voice mode"); continue
                process_command(cmd_text, audio_obj=audio_cmd)
            except SystemExit:
                resp_print_say("Friday offline"); break
            except Exception as e:
                print("Processing error:", e); resp_print_say("Error occurred")
            finally:
                # return to idle pulse
                gui.stop_pulse()
                gui.start_pulse()
        time.sleep(0.12)

# ---------- startup GUI ----------
root = tk.Tk()
gui = FridayGUI(root)
gui.apply_theme()
greet = "Siri style voice ready." if cfg.get("voice_index")=="siri" else "Jarvis style online." if cfg.get("voice_index")=="jarvis" else "Gentleman mode active."
resp_print_say(greet)

# run tk loop
try:
    root.mainloop()
except KeyboardInterrupt:
    print("Interrupted")
