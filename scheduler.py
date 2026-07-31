import sqlite3, threading, time, json, random, re
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "scheduler.db"

class SmartScheduler:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, description TEXT, trigger_type TEXT, trigger_value TEXT, action_type TEXT, action_config TEXT, enabled INTEGER DEFAULT 1, last_run TEXT, next_run TEXT, created_at TEXT)")
        self._conn.commit()
        self._running = False
        self._thread = None

    def add_task(self, name, description, trigger_type, trigger_value, action_type, action_config):
        now = datetime.now().isoformat()
        next_run = self._calc_next_run(trigger_type, trigger_value)
        self._conn.execute(
            "INSERT INTO tasks (name, description, trigger_type, trigger_value, action_type, action_config, enabled, last_run, next_run, created_at) VALUES (?,?,?,?,?,?,1,?,?,?)",
            (name, description, trigger_type, trigger_value, action_type, json.dumps(action_config), "", next_run, now))
        self._conn.commit()
        return self._conn.execute("SELECT id FROM tasks ORDER BY id DESC LIMIT 1").fetchone()[0]

    def _calc_next_run(self, trigger_type, trigger_value):
        now = datetime.now()
        if trigger_type == "interval":
            mins = int(trigger_value.rstrip("m"))
            return (now + timedelta(minutes=mins)).isoformat()
        if trigger_type == "daily":
            h, m = map(int, trigger_value.split(":"))
            t = now.replace(hour=h, minute=m, second=0)
            if t <= now: t += timedelta(days=1)
            return t.isoformat()
        if trigger_type == "hourly":
            m = int(trigger_value.rstrip("m"))
            t = now.replace(minute=m, second=0)
            if t <= now: t += timedelta(hours=1)
            return t.isoformat()
        return (now + timedelta(hours=1)).isoformat()

    def list_tasks(self):
        cur = self._conn.execute("SELECT * FROM tasks ORDER BY next_run ASC")
        rows = []
        for r in cur.fetchall():
            try:
                config = json.loads(r[6]) if r[6] else {}
            except:
                config = {}
            rows.append({"id": r[0], "name": r[1], "description": r[2], "trigger_type": r[3], "trigger_value": r[4], "action_type": r[5], "action_config": config, "enabled": bool(r[7]), "last_run": r[8], "next_run": r[9], "created_at": r[10]})
        return rows

    def delete_task(self, tid):
        self._conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
        self._conn.commit()
        return True

    def toggle_task(self, tid):
        self._conn.execute("UPDATE tasks SET enabled = CASE WHEN enabled THEN 0 ELSE 1 END WHERE id=?", (tid,))
        self._conn.commit()
        return True

    def start(self, callback=None):
        if self._running: return
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(callback,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self, callback):
        while self._running:
            try:
                now = datetime.now()
                cur = self._conn.execute("SELECT * FROM tasks WHERE enabled=1 AND next_run <= ?", (now.isoformat(),))
                for r in cur.fetchall():
                    task = {"id": r[0], "name": r[1], "action_type": r[5]}
                    try:
                        config = json.loads(r[6]) if r[6] else {}
                    except:
                        config = {}
                    if callback:
                        try:
                            callback(task, config)
                        except:
                            pass
                    next_run = self._calc_next_run(r[3], r[4])
                    self._conn.execute("UPDATE tasks SET last_run=?, next_run=? WHERE id=?", (now.isoformat(), next_run, r[0]))
                self._conn.commit()
            except:
                pass
            time.sleep(30)

    def parse_natural(self, text):
        t = text.lower()
        # "every X minutes/hourly/daily"
        m = re.match(r"every\s+(\d+)\s*(m|min|minute|minutes)", t)
        if m: return ("interval", f"{m.group(1)}m", "notify")
        m = re.search(r"daily\s*(?:at\s+)?(\d{1,2}):?(\d{2})?", t)
        if m:
            h, mi = m.group(1), m.group(2) or "00"
            return ("daily", f"{h.zfill(2)}:{mi}", "notify")
        m = re.search(r"hourly\s*(?:at\s+)?(\d{1,2})", t)
        if m: return ("hourly", f"{m.group(1)}", "notify")
        return None

    def close(self):
        self._running = False
        self._conn.close()
