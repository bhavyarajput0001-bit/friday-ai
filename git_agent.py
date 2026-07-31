import subprocess, os, json, re
from pathlib import Path

class GitAgent:
    def __init__(self):
        self._repo_path = None
        self._pending_action = None
        self.permission_required = True

    def _find_repo(self, path=None):
        path = path or os.getcwd()
        try:
            r = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5, cwd=path)
            if r.returncode == 0:
                self._repo_path = r.stdout.strip()
                return self._repo_path
        except: pass
        return None

    def set_repo(self, path):
        if os.path.isdir(path):
            self._repo_path = path
            return True
        return False

    def run(self, *args, skip_permission=False):
        if not self._repo_path:
            self._find_repo()
            if not self._repo_path:
                return {"error": "No git repository found. Use 'git init' or set a repo path."}
        if self.permission_required and not skip_permission:
            cmd = " ".join(args)
            self._pending_action = {"args": args, "cmd": cmd}
            return {"pending": True, "cmd": cmd, "message": f"Run `git {cmd}`? Reply 'yes' to execute."}
        try:
            r = subprocess.run(["git"] + list(args), capture_output=True, text=True, timeout=30, cwd=self._repo_path)
            return {"output": r.stdout.strip(), "error": r.stderr.strip() if r.returncode != 0 else "", "success": r.returncode == 0}
        except Exception as e:
            return {"error": str(e)}

    def confirm_pending(self):
        if self._pending_action:
            args = self._pending_action["args"]
            self._pending_action = None
            return self.run(*args, skip_permission=True)
        return {"error": "No pending action"}

    def cancel_pending(self):
        self._pending_action = None
        return {"status": "cancelled"}

    def status(self):
        return self.run("status", "--short", skip_permission=True)

    def diff(self):
        return self.run("diff", skip_permission=True)

    def log(self, count=5):
        return self.run("log", f"--oneline", "-n", str(count), skip_permission=True)

    def add(self, files="."):
        return self.run("add", files)

    def commit(self, message):
        return self.run("commit", "-m", message)

    def push(self):
        return self.run("push")

    def pull(self):
        return self.run("pull")

    def init(self, path=None):
        path = path or os.getcwd()
        try:
            r = subprocess.run(["git", "init"], capture_output=True, text=True, timeout=10, cwd=path)
            if r.returncode == 0:
                self._repo_path = path
                return {"output": "Git repository initialized"}
            return {"error": r.stderr.strip()}
        except Exception as e:
            return {"error": str(e)}

    def parse_command(self, text):
        t = text.lower().strip()
        if "git status" in t: return self.status()
        if "git diff" in t: return self.diff()
        if "git log" in t: return self.log()
        m = re.match(r"git add\s+(.+)", t)
        if m: return self.add(m.group(1))
        m = re.match(r'git commit\s+(?:-m\s+)?["\']?(.+?)["\']?$', t)
        if m: return self.commit(m.group(1))
        if "git push" in t: return self.push()
        if "git pull" in t: return self.pull()
        if "git init" in t: return self.init()
        m = re.match(r"git\s+(.+)", t)
        if m: return self.run(*m.group(1).split())
        return None

    def format_for_chat(self, result):
        if "pending" in result:
            return f"🔐 {result['message']}"
        if "error" in result:
            return f"⚠️ {result['error']}"
        if result.get("output"):
            return f"```\n{result['output']}\n```"
        if result.get("success"):
            return "✅ Done"
        return str(result)
