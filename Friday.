# Friday.py
# FINAL optimized smooth Jarvis-style AI assistant
# Mac GUI, threaded voice/text, double-clap wake, TTS, Hinglish, self-learning

import os, sys, json, threading, time, subprocess, re, audioop
from pathlib import Path

# Libraries with import check
try:
    import speech_recognition as sr
    from deep_translator import GoogleTranslator
    import tkinter as tk
    from tkinter import simpledialog, messagebox
except Exception as e:
    print("Missing libraries. Install:\nbrew install portaudio\npip3 install speechrecognition deep-translator pyaudio")
    raise

# ---------- CONFIG & MEMORY ----------
HOME = Path.home()
APP_DIR = HOME / "PersonalAssistant"
APP_DIR.mkdir(exist_ok=True)
MEM_FILE = APP_DIR / "friday_memory.json"

DEFAULT_CFG = {
    "mode": "interact",   # voice or interact
    "voice_index": "siri", # siri / jarvis / gentleman
    "speak_on": False,
    "clap_trigger": False,
    "wake_word": "friday",
    "clap_thresh": 2000,
    "listen_timeout": 5,
    "continuous_listen": False
}

if MEM_FILE.exists():
    try:
        data = json.load(open(MEM_FILE,"r"))
        cfg = data.get("cfg", DEFAULT_CFG.copy())
        custom_cmds = data.get("custom_cmds",{})
    except:
        cfg = DEFAULT_CFG.copy()
        custom_cmds = {}
else:
    cfg = DEFAULT_CFG.copy()
    custom_cmds = {}

def save_memory():
    json.dump({"cfg":cfg,"custom_cmds":custom_cmds}, open(MEM_FILE,"w"), indent=2)

# ---------- VOICE MAPPING ----------
VOICE_MAP = {"siri":"Samantha", "jarvis":"Alex", "gentleman":"Tom"}
if cfg.get("voice_index") not in VOICE_MAP:
    cfg["voice_index"] = "siri"

def tts(text):
    if not cfg.get("speak_on",False): return
    voice = VOICE_MAP.get(cfg.get("voice_index","siri"),"Samantha")
    try:
        subprocess.Popen(["say","-v",voice,text])
    except: pass

# ---------- SPEECH RECOGNITION ----------
r = sr.Recognizer()
def listen_audio(timeout=None, phrase_time_limit=5):
    with sr.Microphone() as source:
        if timeout:
            audio = r.listen(source,timeout=timeout,phrase_time_limit=phrase_time_limit)
        else:
            audio = r.listen(source,phrase_time_limit=phrase_time_limit)
    return audio

def recognize_audio(audio):
    try: return r.recognize_google(audio).lower()
    except: return ""

# ---------- DOUBLE CLAP DETECTION ----------
def detect_double_clap(single_window=0.6, thresh=None):
    if thresh is None:
        thresh = cfg.get("clap_thresh",2000)
    try:
        a1 = listen_audio(timeout=1, phrase_time_limit=single_window)
        rms1 = audioop.rms(a1.get_raw_data(convert_rate=16000, convert_width=2),2)
        if rms1<thresh: return False
        a2 = listen_audio(timeout=1, phrase_time_limit=single_window)
        rms2 = audioop.rms(a2.get_raw_data(convert_rate=16000, convert_width=2),2)
        return rms2>=thresh
    except: return False

# ---------- EMOTION DETECTION ----------
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
        if rms>3500: return "strong"
    except: pass
    return "neutral"

# ---------- NORMALIZER ----------
def normalize_command(text):
    t = text.lower()
    t=t.replace("khol de","open").replace("kholna","open").replace("kholo","open")
    t=t.replace("chala do","open").replace("band ho ja","stop").replace("band kar","stop")
    t=t.replace("volume set kar","volume").replace("spotify chalo","open spotify")
    t=t.replace("whatsapp app","open whatsapp")
    t=re.sub(r"\bchrome\b","open chrome",t)
    t=re.sub(r"\bbrave\b","open brave",t)
    t=t.replace("chat gpt","open chatgpt")
    t=t.replace("please","").replace("pls","").strip()
    return " ".join(t.split())

# ---------- ACTIONS ----------
def resp_print_say(msg,emotion=None):
    out=msg if len(msg)<120 else msg.split(".")[0] if cfg["mode"]=="voice" else msg
    if cfg["mode"]!="voice" and emotion=="negative": out=f"{msg}. Focus. Solution first."
    print("FRIDAY:",out)
    tts(out)

def open_chrome(): subprocess.Popen(["open","-a","Google Chrome"]); resp_print_say("Chrome opened")
def open_brave(): subprocess.Popen(["open","-a","Brave Browser"]); resp_print_say("Brave opened")
def open_whatsapp(): subprocess.Popen(["open","-a","WhatsApp"]); resp_print_say("WhatsApp opened")
def open_spotify(): subprocess.Popen(["open","-a","Spotify"]); resp_print_say("Spotify opened")
def open_chatgpt(): subprocess.Popen(["open","https://chat.openai.com"]); resp_print_say("ChatGPT opened")
def open_url(url): subprocess.Popen(["open",url]); resp_print_say(f"Opening {url}")
def set_volume(level): subprocess.Popen(["osascript","-e",f"set volume output volume {int(level)}"]); resp_print_say(f"Volume set to {level}")
def set_timer_minutes(mins): resp_print_say(f"Timer set for {mins} minutes"); time.sleep(int(mins)*60); resp_print_say("Timer finished")
def translate_text(cmd):
    try: parts=cmd.split("translate")[-1].strip().split("to"); out=GoogleTranslator(source='auto',target=parts[1].strip()).translate(parts[0].strip()); resp_print_say("Translated: "+out)
    except: resp_print_say("Translation failed")

def learn_new_command(raw):
    try: name,action=raw.split(":",1); name=name.strip(); action=action.strip(); custom_cmds[name]=action; save_memory(); resp_print_say(f"Learned {name}")
    except: resp_print_say("Learning failed. Use: name:action")

def run_custom(name):
    action=custom_cmds.get(name)
    if not action: resp_print_say("Command not found"); return
    if action.startswith("open "):
        target=action.replace("open ","").strip()
        if target.startswith("http"): open_url(target)
        else: subprocess.Popen(["open","-a",target]); resp_print_say(f"Executed {name}")
    else: subprocess.Popen(action.split()); resp_print_say(f"Executed {name}")

# ---------- COMMAND PROCESSOR ----------
def process_command(cmd,audio_obj=None):
    normalized=normalize_command(cmd)
    em=detect_emotion_text(cmd)
    if audio_obj: em_s=detect_emotion_audio(audio_obj); em="negative" if em_s!="neutral" else em
    if "learn command" in normalized: learn_new_command(normalized); return
    if normalized in custom_cmds: run_custom(normalized); return
    if "open chrome" in normalized: open_chrome()
    elif "open brave" in normalized: open_brave()
    elif "open whatsapp" in normalized: open_whatsapp()
    elif "open spotify" in normalized: open_spotify()
    elif "open chatgpt" in normalized: open_chatgpt()
    elif "open " in normalized and "http" in normalized: open_url(normalized.split("open",1)[1].strip())
    elif "translate" in normalized: translate_text(normalized)
    elif "timer" in normalized: m=re.search(r"(\d+)",normalized); set_timer_minutes(m.group(1)) if m else resp_print_say("Timer minutes not found")
    elif "volume" in normalized: m=re.search(r"(\d+)",normalized); set_volume(m.group(1)) if m else resp_print_say("Specify volume 0-100")
    elif "switch to voice" in normalized or "voice mode" in normalized: cfg["mode"]="voice"; save_memory(); resp_print_say("Voice mode on",em)
    elif "switch to interact" in normalized or "interact mode" in normalized: cfg["mode"]="interact"; save_memory(); resp_print_say("Interact mode on",em)
    elif "voice jarvis" in normalized or "voice one" in normalized: cfg["voice_index"]="jarvis"; save_memory(); resp_print_say("Jarvis voice selected")
    elif "voice siri" in normalized or "voice two" in normalized: cfg["voice_index"]="siri"; save_memory(); resp_print_say("Siri voice selected")
    elif "voice gentleman" in normalized or "voice three" in normalized: cfg["voice_index"]="gentleman"; save_memory(); resp_print_say("Gentleman voice selected")
    elif "speak on" in normalized or "friday speak" in normalized: cfg["speak_on"]=True; save_memory(); resp_print_say("Speech on")
    elif "mute" in normalized or "speak off" in normalized or "friday mute" in normalized: cfg["speak_on"]=False; save_memory(); resp_print_say("Speech off")
    elif "enable clap" in normalized: cfg["clap_trigger"]=True; save_memory(); resp_print_say("Clap trigger enabled")
    elif "disable clap" in normalized: cfg["clap_trigger"]=False; save_memory(); resp_print_say("Clap trigger disabled")
    elif "stop" in normalized or "exit" in normalized or "band ho ja" in normalized: resp_print_say("Shutting down"); raise SystemExit
    else:
        if normalized.startswith("open "):
            target=normalized.split("open ",1)[1].strip()
            if target.startswith("http"): open_url(target)
            else: subprocess.Popen(["open","-a",target.title()]); resp_print_say(f"Opening {target}")
        else: resp_print_say("Command not recognized",emotion=em)

# ---------- GUI ----------
class FridayGUI:
    def __init__(self,root):
        self.root=root
        root.title("Friday - Personal Assistant")
        root.geometry("420x220")
        self.status_var=tk.StringVar(); self.status_var.set(f"Mode: {cfg['mode']} | TTS: {'On' if cfg['speak_on'] else 'Off'} | Clap: {'On' if cfg['clap_trigger'] else 'Off'}")
        tk.Label(root,text="Friday",font=("Helvetica",18,"bold")).pack(pady=6)
        tk.Label(root,textvariable=self.status_var).pack(pady=4)
        frm=tk.Frame(root); frm.pack(pady=6)
        tk.Button(frm,text="Start",width=10,command=self.start).grid(row=0,column=0,padx=6)
        tk.Button(frm,text="Stop",width=10,command=self.stop).grid(row=0,column=1,padx=6)
        tk.Button(frm,text="Voice",width=10,command=self.toggle_voice).grid(row=1,column=0,padx=6,pady=6)
        tk.Button(frm,text="Clap On/Off",width=10,command=self.toggle_clap).grid(row=1,column=1,padx=6,pady=6)
        tk.Button(root,text="Learn Command",command=self.manual_learn).pack(pady=4)
        tk.Button(root,text="Show Memory Folder",command=self.open_memory_folder).pack(pady=3)
        self.running=False
        self.thread=None

    def refresh_status(self): self.status_var.set(f"Mode: {cfg['mode']} | TTS: {'On' if cfg['speak_on'] else 'Off'} | Clap: {'On' if cfg['clap_trigger'] else 'Off'}")
    def start(self):
        if self.running: messagebox.showinfo("Friday","Already running"); return
        self.running=True
        self.thread=threading.Thread(target=main_loop,daemon=True)
        self.thread.start()
        self.refresh_status()
    def stop(self): self.running=False; resp_print_say("Stopping Friday")
    def toggle_voice(self): cfg["speak_on"]=not cfg.get("speak_on",False); save_memory(); self.refresh_status(); resp_print_say("Speech toggled")
    def toggle_clap(self): cfg["clap_trigger"]=not cfg.get("clap_trigger",False); save_memory(); self.refresh_status(); resp_print_say("Clap toggled")
    def manual_learn(self):
        raw=simpledialog.askstring("Learn command","Format: name:action\nE.g. instagram:open https://instagram.com")
        if raw: learn_new_command(raw)
    def open_memory_folder(self): subprocess.Popen(["open",str(APP_DIR)])

# ---------- MAIN LOOP ----------
gui=None
def main_loop():
    global gui
    resp_print_say("Friday online.")
    while True:
        if gui and not gui.running: time.sleep(0.4); continue
        triggered=False
        if cfg.get("clap_trigger",False) and detect_double_clap(): triggered=True
        if not triggered and cfg.get("continuous_listen",False):
            try: audio=listen_audio(timeout=1,phrase_time_limit=5); text=recognize_audio(audio); process_command(text,audio_obj=audio); continue
            except: pass
        if not triggered:
            try: audio=listen_audio(timeout=1,phrase_time_limit=3); text=recognize_audio(audio); triggered=(cfg["wake_word"] in text)
            except: continue
        if triggered:
            resp_print_say("Yes?")
            try:
                audio_cmd=listen_audio(timeout=cfg.get("listen_timeout",5),phrase_time_limit=7)
                cmd_text=recognize_audio(audio_cmd)
                if not cmd_text: resp_print_say("Didn't catch that"); continue
                print("Command heard:",cmd_text)
                if "switch to text" in cmd_text or "switch to interact" in cmd_text: cfg["mode"]="interact"; save_memory(); resp_print_say("Switched to interact mode"); continue
                if "switch to voice" in cmd_text or "voice mode" in cmd_text: cfg["mode"]="voice"; save_memory(); resp_print_say("Switched to voice mode"); continue
                process_command(cmd_text,audio_obj=audio_cmd)
            except SystemExit: resp_print_say("Friday offline"); break
            except Exception as e: print("Error:",e); resp_print_say("Error occurred")
        time.sleep(0.2)

# ---------- RUN GUI ----------
root=tk.Tk()
gui=FridayGUI(root)
greet_voice="Siri style voice ready." if cfg["voice_index"]=="siri" else "Jarvis style online." if cfg["voice_index"]=="jarvis" else "Gentleman mode active."
resp_print_say(greet_voice)
try: root.mainloop()
except KeyboardInterrupt: print("Interrupted by user")












































