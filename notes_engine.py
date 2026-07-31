import os, subprocess, json, sqlite3, threading, re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "notes.db"

GOOGLE_KEEP = False
try:
    import gkeepapi
    GOOGLE_KEEP = True
except: pass

class NotesEngine:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, title TEXT, body TEXT, source TEXT DEFAULT 'local', source_id TEXT, folder TEXT DEFAULT '', synced INTEGER DEFAULT 1, updated_at TEXT)")
        self._conn.commit()
        self._keep = None

    def _keep_connect(self):
        if not GOOGLE_KEEP: return False
        if self._keep: return True
        cfg = DATA_DIR / "google_keep.json"
        if not cfg.exists(): return False
        try:
            creds = json.loads(cfg.read_text())
            self._keep = gkeepapi.Keep()
            self._keep.login(creds.get("email", ""), creds.get("password", ""))
            return True
        except: return False

    def _run_apple_script(self, script):
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return r.stdout.strip()
        except: return ""

    def get_apple_notes(self):
        script = '''
        tell application "Notes"
            set output to ""
            set noteCount to count of notes
            if noteCount > 0 then
                repeat with n in notes 1 thru 10
                    set output to output & (name of n) & "|" & (body of n) & "\\n---\\n"
                end repeat
            end if
            return output
        end tell
        '''
        result = self._run_apple_script(script)
        if not result: return []
        notes = []
        for block in result.split("\n---\n"):
            if "|" in block:
                parts = block.split("|", 1)
                notes.append({"title": parts[0].strip(), "body": parts[1].strip()[:500] if len(parts) > 1 else ""})
        return notes

    def create_apple_note(self, title, body=""):
        script = f'''
        tell application "Notes"
            make new note at folder "Notes" with properties {{name:"{title}", body:"{body}"}}
        end tell
        '''
        self._run_apple_script(script)
        return True

    def get_local_notes(self, folder=""):
        cur = self._conn.execute("SELECT * FROM notes ORDER BY updated_at DESC LIMIT 20")
        return [dict(r) for r in cur.fetchall()]

    def create_local_note(self, title, body="", folder=""):
        import uuid
        eid = str(uuid.uuid4())[:12]
        now = datetime.now().isoformat()
        self._conn.execute("INSERT INTO notes VALUES (?,?,?,?,?,?,?,?)", (eid, title, body, "local", "", folder, 1, now))
        self._conn.commit()
        return eid

    def get_keep_notes(self):
        if not self._keep_connect(): return []
        try:
            notes = self._keep.find()
            return [{"title": n.title, "body": n.text[:500], "source_id": n.id} for n in list(notes)[:10]]
        except: return []

    def create_keep_note(self, title, body=""):
        if not self._keep_connect(): return None
        try:
            n = self._keep.createNote(title, body)
            self._keep.sync()
            return n.id
        except: return None

    def all_notes(self):
        notes = {"local": self.get_local_notes(), "apple": self.get_apple_notes()}
        if GOOGLE_KEEP:
            try: notes["keep"] = self.get_keep_notes()
            except: notes["keep"] = []
        return notes

    def close(self):
        self._conn.close()


class EmailEngine:
    def __init__(self):
        self._gmail = None

    def _gmail_connect(self):
        if self._gmail: return True
        try:
            import pickle
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            token_path = DATA_DIR / "gmail_token.pickle"
            creds_path = DATA_DIR / "google_credentials.json"
            if not creds_path.exists(): return False
            creds = None
            if token_path.exists():
                creds = pickle.loads(token_path.read_bytes())
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), ["https://www.googleapis.com/auth/gmail.readonly"])
                    creds = flow.run_local_server(port=0)
                token_path.write_bytes(pickle.dumps(creds))
            self._gmail = build("gmail", "v1", credentials=creds)
            return True
        except: return False

    def get_gmail(self, max_results=5):
        if not self._gmail_connect(): return []
        try:
            results = self._gmail.users().messages().list(userId="me", maxResults=max_results, q="in:inbox").execute()
            messages = []
            for msg in results.get("messages", []):
                data = self._gmail.users().messages().get(userId="me", id=msg["id"]).execute()
                headers = {h["name"]: h["value"] for h in data["payload"]["headers"]}
                messages.append({"id": msg["id"], "from": headers.get("From", ""), "subject": headers.get("Subject", ""), "snippet": data.get("snippet", "")[:200]})
            return messages
        except: return []

    def get_apple_mail(self):
        script = '''
        tell application "Mail"
            set output to ""
            set msgCount to count of messages of inbox
            if msgCount > 0 then
                repeat with m in messages of inbox 1 thru 5
                    set output to output & (subject of m) & "|" & (sender of m) & "\\n"
                end repeat
            end if
            return output
        end tell
        '''
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            messages = []
            for line in r.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 1)
                    messages.append({"subject": parts[0], "from": parts[1] if len(parts) > 1 else ""})
            return messages
        except: return []

    def all_mail(self):
        mail = {"apple": self.get_apple_mail()}
        try: mail["gmail"] = self.get_gmail()
        except: mail["gmail"] = []
        return mail

    def send_apple_mail(self, to, subject, body):
        script = f'''
        tell application "Mail"
            set newMsg to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
            tell newMsg
                make new to recipient at end of to recipients with properties {{address:"{to}"}}
            end tell
            send newMsg
        end tell
        '''
        try:
            subprocess.run(["osascript", "-e", script], timeout=10)
            return True
        except: return False
