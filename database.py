import sqlite3
import json
from pathlib import Path
from datetime import datetime

class FridayDB:
    def __init__(self):
        self.db_path = Path(__file__).parent / "data" / "friday_v4.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        with self._get_conn() as conn:
            # Tasks table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    priority TEXT DEFAULT 'medium',
                    due TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Agenda table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agenda (
                    id TEXT PRIMARY KEY,
                    time TEXT,
                    title TEXT,
                    duration TEXT,
                    highlight INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Knowledge table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE,
                    count INTEGER DEFAULT 0,
                    label TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # History log for context tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    app_name TEXT,
                    window_title TEXT,
                    duration INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Seed internal knowledge if empty
            count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
            if count == 0:
                defaults = [
                    ('k1', 'projects', 22, 'Files'),
                    ('k2', 'notes', 128, 'Items'),
                    ('k3', 'research', 14, 'Sources'),
                    ('k4', 'voice_memos', 9, 'Recordings')
                ]
                conn.executemany("INSERT INTO knowledge (id, key, count, label) VALUES (?,?,?,?)", defaults)

    # --- TASKS ---
    def get_tasks(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def add_task(self, id, title, priority='medium', due=''):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO tasks (id, title, priority, due) VALUES (?,?,?,?)", (id, title, priority, due))

    def update_task(self, id, status=None, progress=None):
        with self._get_conn() as conn:
            if status is not None:
                conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, id))
            if progress is not None:
                conn.execute("UPDATE tasks SET progress = ? WHERE id = ?", (progress, id))

    def delete_task(self, id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (id,))

    # --- AGENDA ---
    def get_agenda(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM agenda ORDER BY created_at ASC").fetchall()
            return [dict(r) for r in rows]

    def add_agenda(self, id, time, title, duration='', highlight=0):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO agenda (id, time, title, duration, highlight) VALUES (?,?,?,?,?)",
                         (id, time, title, duration, highlight))

    def delete_agenda(self, id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM agenda WHERE id = ?", (id,))

    # --- KNOWLEDGE ---
    def get_knowledge(self):
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM knowledge").fetchall()
            return {r['key']: {'count': r['count'], 'label': r['label']} for r in rows}

    def update_knowledge(self, key, delta=1):
        with self._get_conn() as conn:
            conn.execute("UPDATE knowledge SET count = count + ?, updated_at = ? WHERE key = ?",
                         (delta, datetime.now(), key))

    # --- CONTEXT HISTORY ---
    def log_context(self, app_name, window_title, duration):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO history (app_name, window_title, duration) VALUES (?,?,?)",
                         (app_name, window_title, duration))

    def get_productivity_data(self):
        # Very simple productivity heuristic: categorize apps
        productive_apps = ['Code', 'Xcode', 'Terminal', 'iTerm2', 'Postman', 'Notion', 'Slack']
        with self._get_conn() as conn:
            total = conn.execute("SELECT SUM(duration) FROM history WHERE date(timestamp) = date('now')").fetchone()[0] or 1
            prod = conn.execute("SELECT SUM(duration) FROM history WHERE date(timestamp) = date('now') AND app_name IN ({})".format(
                ','.join(['?']*len(productive_apps))
            ), productive_apps).fetchone()[0] or 0
            return int((prod / total) * 100)
