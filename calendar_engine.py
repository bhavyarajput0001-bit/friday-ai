import os, json, sqlite3, threading, time, subprocess, re
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "calendar.db"
CONFIG_PATH = DATA_DIR / "calendar_config.json"

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class LocalStore:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration INTEGER DEFAULT 30,
                location TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                all_day INTEGER DEFAULT 0,
                source TEXT DEFAULT 'local',
                source_id TEXT DEFAULT '',
                synced INTEGER DEFAULT 1,
                updated_at TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                action TEXT,
                timestamp TEXT
            )
        """)
        self._conn.commit()

    def _now(self):
        return datetime.now().isoformat()

    def add_event(self, title, start_time, duration=30, location="", notes="", all_day=False, source="local", source_id="", synced=True):
        import uuid
        eid = str(uuid.uuid4())[:12]
        end_time = self._calc_end(start_time, duration)
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (eid, title, start_time, end_time, duration, location, notes, 1 if all_day else 0,
                 source, source_id, 1 if synced else 0, self._now())
            )
            self._conn.commit()
        return eid

    def update_event(self, eid, **kwargs):
        fields = []
        vals = []
        for k, v in kwargs.items():
            if k in ("title", "start_time", "duration", "location", "notes", "all_day", "source", "source_id", "synced"):
                fields.append(f"{k}=?")
                vals.append(v)
        if not fields: return False
        if "start_time" in kwargs and "duration" in kwargs.get("duration", None):
            end_time = self._calc_end(kwargs["start_time"], kwargs.get("duration", 30))
            fields.append("end_time=?")
            vals.append(end_time)
        vals.append(self._now())
        vals.append(eid)
        with self._lock:
            self._conn.execute(f"UPDATE events SET {', '.join(fields)}, updated_at=? WHERE id=?", vals)
            self._conn.commit()
        return True

    def delete_event(self, eid):
        with self._lock:
            self._conn.execute("DELETE FROM events WHERE id=?", (eid,))
            self._conn.commit()

    def get_events(self, start_date=None, end_date=None, limit=50):
        with self._lock:
            if start_date and end_date:
                cur = self._conn.execute(
                    "SELECT * FROM events WHERE start_time >= ? AND start_time <= ? ORDER BY start_time LIMIT ?",
                    (start_date, end_date, limit)
                )
            else:
                cur = self._conn.execute("SELECT * FROM events WHERE start_time >= ? ORDER BY start_time LIMIT ?",
                                        (self._now()[:10], limit))
            return [dict(r) for r in cur.fetchall()]

    def get_event(self, eid):
        with self._lock:
            cur = self._conn.execute("SELECT * FROM events WHERE id=?", (eid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_unsynced(self):
        with self._lock:
            cur = self._conn.execute("SELECT * FROM events WHERE synced=0")
            return [dict(r) for r in cur.fetchall()]

    def mark_synced(self, eid):
        with self._lock:
            self._conn.execute("UPDATE events SET synced=1 WHERE id=?", (eid,))
            self._conn.commit()

    def _calc_end(self, start_iso, duration_min):
        try:
            st = datetime.fromisoformat(start_iso)
            return (st + timedelta(minutes=duration_min)).isoformat()
        except:
            return start_iso

    def close(self):
        self._conn.close()


class AppleCalendar:
    def __init__(self):
        self.available = self._check()

    def _check(self):
        try:
            r = subprocess.run(["osascript", "-e", 'tell application "System Events" to exists (process "Calendar")'],
                             capture_output=True, text=True, timeout=3)
            return True
        except: return False

    def get_events(self, days=7):
        if not self.available: return []
        script = f'''
        set output to ""
        tell application "Calendar"
            set calNames to name of every calendar
            repeat with calName in calNames
                tell calendar calName
                    set today to (current date)
                    set future to today + {days} * days
                    set todayEvents to every event whose start date ≥ today and start date < future
                    repeat with e in todayEvents
                        set output to output & (summary of e) & "|" & (start date of e) & "|" & (end date of e) & "|" & (location of e) & "|" & calName & "\\n"
                    end repeat
                end tell
            end repeat
        end tell
        return output
        '''
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            events = []
            for line in r.stdout.strip().split("\n"):
                if not line: continue
                parts = line.split("|")
                if len(parts) >= 3:
                    events.append({"title": parts[0], "start": parts[1], "end": parts[2],
                                  "location": parts[3] if len(parts) > 3 else "", "calendar": parts[4] if len(parts) > 4 else "Calendar"})
            return events
        except: return []

    def create_event(self, title, start_time, end_time, location="", calendar="Calendar"):
        try:
            script = f'''
            tell application "Calendar"
                tell calendar "{calendar}"
                    make new event at end with properties {{{{summary:"{title}", start date:date "{start_time}", end date:date "{end_time}", location:"{location}"}}}}
                end tell
            end tell
            '''
            subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return True
        except: return False


class GoogleCalendar:
    def __init__(self):
        self.available = False
        self.service = None
        self._load_creds()

    def _load_creds(self):
        import pickle
        token_path = DATA_DIR / "google_calendar_token.pickle"
        creds_path = DATA_DIR / "google_credentials.json"
        if not creds_path.exists():
            return
        try:
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow
            creds = None
            if token_path.exists():
                creds = pickle.loads(token_path.read_bytes())
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                    creds = flow.run_local_server(port=0)
                token_path.write_bytes(pickle.dumps(creds))
            from googleapiclient.discovery import build
            self.service = build("calendar", "v3", credentials=creds)
            self.available = True
        except Exception as e:
            print(f"[GoogleCalendar] Init error: {e}")

    def get_events(self, days=7):
        if not self.available: return []
        try:
            now = datetime.utcnow().isoformat() + "Z"
            future = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
            events = self.service.events().list(
                calendarId="primary", timeMin=now, timeMax=future,
                singleEvents=True, orderBy="startTime"
            ).execute()
            return [{
                "title": e.get("summary", ""),
                "start": e["start"].get("dateTime", e["start"].get("date", "")),
                "end": e["end"].get("dateTime", e["end"].get("date", "")),
                "location": e.get("location", ""),
                "source_id": e.get("id", ""),
            } for e in events.get("items", [])]
        except: return []

    def create_event(self, title, start_time, end_time, location=""):
        if not self.available: return None
        try:
            event = {
                "summary": title,
                "start": {"dateTime": start_time, "timeZone": "Asia/Kolkata"},
                "end": {"dateTime": end_time, "timeZone": "Asia/Kolkata"},
                "location": location,
            }
            e = self.service.events().insert(calendarId="primary", body=event).execute()
            return e.get("id")
        except: return None


class CalendarEngine:
    def __init__(self):
        self.local = LocalStore()
        self.apple = AppleCalendar()
        self.google = GoogleCalendar()

    def get_events(self, days=7):
        start = datetime.now().isoformat()
        end = (datetime.now() + timedelta(days=days)).isoformat()
        return self.local.get_events(start, end)

    def get_event(self, eid):
        return self.local.get_event(eid)

    def create_event(self, title, start_time, duration=30, location="", notes="", all_day=False):
        eid = self.local.add_event(title, start_time, duration, location, notes, all_day, synced=False)
        threading.Thread(target=self._sync_out, args=(eid, title, start_time, duration, location), daemon=True).start()
        return eid

    def delete_event(self, eid):
        self.local.delete_event(eid)

    def update_event(self, eid, **kwargs):
        return self.local.update_event(eid, **kwargs)

    def _sync_out(self, eid, title, start_time, duration, location):
        try:
            st = datetime.fromisoformat(start_time)
            end = (st + timedelta(minutes=duration)).isoformat()
            src = "local"
            sid = ""
            if self.apple.available:
                try:
                    self.apple.create_event(title, start_time, end, location)
                    src = "apple"
                except: pass
            if self.google.available:
                gid = self.google.create_event(title, start_time, end, location)
                if gid:
                    src = "google"
                    sid = gid
            self.local.update_event(eid, source=src, source_id=sid, synced=True)
        except: pass

    def sync_from_apple(self):
        if not self.apple.available: return []
        apple_events = self.apple.get_events(7)
        synced = []
        for ae in apple_events:
            existing = self.local.get_events(ae["start"], ae["end"])
            if not any(e.get("title") == ae["title"] for e in existing):
                try:
                    st = datetime.strptime(ae["start"], "%Y-%m-%d %H:%M:%S").isoformat()
                except:
                    st = datetime.now().isoformat()
                eid = self.local.add_event(ae["title"], st, 60, ae.get("location", ""), source="apple", synced=True)
                synced.append(eid)
        return synced

    def sync_from_google(self):
        if not self.google.available: return []
        google_events = self.google.get_events(7)
        synced = []
        for ge in google_events:
            existing = self.local.get_events(ge["start"], ge["end"])
            if not any(e.get("source_id") == ge["source_id"] for e in existing):
                eid = self.local.add_event(ge["title"], ge["start"], 60, ge.get("location", ""), source="google", source_id=ge["source_id"], synced=True)
                synced.append(eid)
        return synced

    def full_sync(self):
        results = {"apple": 0, "google": 0}
        results["apple"] = len(self.sync_from_apple())
        results["google"] = len(self.sync_from_google())
        return results

    def get_today_summary(self):
        today_start = date.today().isoformat()
        today_end = (date.today() + timedelta(days=1)).isoformat()
        events = self.local.get_events(today_start, today_end)
        return events

    def get_upcoming(self, count=5):
        events = self.local.get_events(limit=count)
        return events

    def parse_natural(self, text):
        """Parse natural language into event data."""
        t = text.lower()
        title = t
        duration = 30
        start_time = datetime.now()

        # Extract time patterns
        time_pat = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', t)
        if time_pat:
            h = int(time_pat.group(1))
            m = int(time_pat.group(2) or 0)
            ampm = time_pat.group(3)
            if ampm == "pm" and h < 12: h += 12
            if ampm == "am" and h == 12: h = 0
            try:
                start_time = start_time.replace(hour=h, minute=m, second=0, microsecond=0)
            except: pass

        # Extract duration
        dur_pat = re.search(r'(\d+)\s*(min|hour|hr)', t)
        if dur_pat:
            val = int(dur_pat.group(1))
            unit = dur_pat.group(2)
            duration = val * 60 if unit.startswith("h") else val

        # Extract date
        if "tomorrow" in t:
            start_time += timedelta(days=1)
        elif "next week" in t:
            start_time += timedelta(days=7)

        # Clean title
        for prefix in ["add event", "create event", "schedule", "remind me to", "add "]:
            if t.startswith(prefix):
                title = t[len(prefix):].strip()
                break

        return {"title": title, "start_time": start_time.isoformat(), "duration": duration}

    def close(self):
        self.local.close()
