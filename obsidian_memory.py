import os, json, re, sqlite3, glob
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "memory.db"

class ObsidianMemory:
    def __init__(self, vault_path=None):
        DATA_DIR.mkdir(exist_ok=True)
        self.vault_path = Path(vault_path or os.path.expanduser("~/Documents/Obsidian"))
        self.vault_path.mkdir(parents=True, exist_ok=True)
        self.notes_dir = self.vault_path / "FRIDAY"
        self.notes_dir.mkdir(exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.execute("CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT, title TEXT, content TEXT, keywords TEXT, created_at TEXT)")
        self._conn.commit()
        self._index_vault()

    def _index_vault(self):
        self._conn.execute("DELETE FROM chunks")
        md_files = list(self.vault_path.rglob("*.md"))
        for f in md_files:
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                title = f.stem
                keywords = " ".join(re.findall(r'\b[A-Z][a-z]{2,}\b', content))
                words = content.split()
                for i in range(0, len(words), 100):
                    chunk = " ".join(words[i:i+100])
                    self._conn.execute("INSERT INTO chunks (file, title, content, keywords, created_at) VALUES (?,?,?,?,?)",
                                       (str(f.relative_to(self.vault_path)), title, chunk[:1000], keywords[:300], datetime.now().isoformat()))
            except: pass
        self._conn.commit()

    def save_conversation(self, user_msg, friday_reply):
        date_str = datetime.now().strftime("%Y-%m-%d")
        convo_file = self.notes_dir / f"{date_str}.md"
        with convo_file.open("a", encoding="utf-8") as f:
            f.write(f"- **You**: {user_msg}\n- **Friday**: {friday_reply}\n\n")
        self._index_vault()
        return str(convo_file.relative_to(self.vault_path))

    def search(self, query, limit=5):
        words = [w for w in re.findall(r'\w{2,}', query.lower()) if w not in ("what", "did", "about", "have", "been", "tell", "where", "when", "why", "how", "the", "and", "you", "your", "our", "past", "this")]
        if not words:
            return []
        conditions = " OR ".join(["(content LIKE ? OR title LIKE ? OR keywords LIKE ?)"] * len(words))
        params = []
        for w in words:
            pattern = f"%{w}%"
            params.extend([pattern, pattern, pattern])
        cur = self._conn.execute(
            f"SELECT file, title, content, keywords FROM chunks WHERE {conditions} LIMIT ?",
            (*params, limit))
        results = []
        for r in cur.fetchall():
            matches = sum(1 for w in words if w.lower() in r[2].lower() or w.lower() in r[3].lower())
            results.append({"file": r[0], "title": r[1], "content": r[2][:300], "keywords": r[3], "score": matches})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def read_note(self, filename):
        fpath = self.vault_path / filename
        if fpath.exists() and fpath.suffix == ".md":
            return fpath.read_text(encoding="utf-8", errors="replace")
        return None

    def list_notes(self, folder=""):
        base = self.vault_path / folder if folder else self.vault_path
        files = sorted(base.rglob("*.md"), key=os.path.getmtime, reverse=True)
        return [{"name": f.name, "path": str(f.relative_to(self.vault_path)), "size": f.stat().st_size, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()} for f in files[:30]]

    def write_note(self, filename, content):
        fpath = self.vault_path / filename
        if not fpath.suffix:
            fpath = fpath.with_suffix(".md")
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
        self._index_vault()
        return str(fpath.relative_to(self.vault_path))

    def get_context(self, query, limit=3):
        results = self.search(query, limit)
        if results:
            context = "\n\n".join([f"# {r['title']}\n{r['content']}" for r in results])
            return context
        return ""

    def close(self):
        self._conn.close()
