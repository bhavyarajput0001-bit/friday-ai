import subprocess, json, urllib.request, urllib.parse, re, threading, time
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
CACHE_PATH = DATA_DIR / "album_art_cache.json"

class MusicController:
    def __init__(self):
        self._current_track = None
        self._art_cache = self._load_cache()
        self._listeners = []

    def _load_cache(self):
        try:
            if CACHE_PATH.exists():
                return json.loads(CACHE_PATH.read_text())
        except: pass
        return {}

    def _save_cache(self):
        DATA_DIR.mkdir(exist_ok=True)
        CACHE_PATH.write_text(json.dumps(self._art_cache, indent=2))

    def _run_script(self, script, timeout=5):
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
            return r.stdout.strip()
        except: return ""

    def _detect_player(self):
        for app in ["Music", "Spotify"]:
            r = self._run_script(f'tell application "System Events" to exists (process "{app}")')
            if r == "true":
                return app
        return None

    def get_current_track(self):
        player = self._detect_player()
        if not player:
            return {"playing": False, "player": None, "title": "No music app running"}

        script = f'''
        tell application "{player}"
            if player state is playing then
                set t to name of current track
                set a to artist of current track
                set al to album of current track
                if "{player}" is "Music" then
                    set dur to duration of current track
                else
                    set dur to 0
                end if
                set pos to player position
                return t & "|" & a & "|" & al & "|" & dur & "|" & pos
            else
                return "paused"
            end if
        end tell
        '''
        result = self._run_script(script)
        if not result or result == "paused":
            return {"playing": False, "player": player, "title": "Paused"}

        parts = result.split("|")
        track = {
            "playing": True,
            "player": player,
            "title": parts[0] if len(parts) > 0 else "Unknown",
            "artist": parts[1] if len(parts) > 1 else "Unknown",
            "album": parts[2] if len(parts) > 2 else "Unknown",
            "duration": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
            "position": float(parts[4]) if len(parts) > 4 and parts[4] else 0,
            "album_art": self._get_album_art(parts[0], parts[1] if len(parts) > 1 else ""),
        }
        self._current_track = track
        return track

    def _get_album_art(self, title, artist):
        key = f"{title} - {artist}"
        if key in self._art_cache:
            return self._art_cache[key]

        try:
            query = urllib.parse.quote(f"{title} {artist} album art")
            url = f"https://itunes.apple.com/search?term={query}&limit=1&entity=song"
            with urllib.request.urlopen(url, timeout=5) as r:
                data = json.loads(r.read())
                if data["resultCount"] > 0:
                    art = data["results"][0].get("artworkUrl100", "")
                    if art:
                        self._art_cache[key] = art
                        self._save_cache()
                        return art
        except: pass
        return ""

    def play(self):
        player = self._detect_player()
        if player:
            self._run_script(f'tell application "{player}" to play')

    def pause(self):
        player = self._detect_player()
        if player:
            self._run_script(f'tell application "{player}" to pause')

    def play_pause(self):
        player = self._detect_player()
        if player:
            self._run_script(f'tell application "{player}" to playpause')

    def next_track(self):
        player = self._detect_player()
        if player:
            self._run_script(f'tell application "{player}" to next track')

    def previous_track(self):
        player = self._detect_player()
        if player:
            self._run_script(f'tell application "{player}" to previous track')

    def set_volume(self, level):
        level = max(0, min(100, int(level)))
        player = self._detect_player()
        if player:
            self._run_script(f'tell application "{player}" to set sound volume to {level}')
        return level

    def get_volume(self):
        player = self._detect_player()
        if player:
            r = self._run_script(f'tell application "{player}" to get sound volume')
            if r: return int(r)
        return 50

    def open_music(self):
        player = self._detect_player() or "Music"
        subprocess.Popen(["open", "-a", player])

    def now_playing_display(self):
        track = self.get_current_track()
        if not track["playing"]:
            return "⏸ Paused" if track["player"] else "🎵 No music app running"
        art = track.get("album_art", "")
        art_line = f"🖼 {art}" if art else ""
        return f"▶ {track['title']} — {track['artist']}\n💿 {track['album']}\n⏱ {int(track['position']//60)}:{(int(track['position'])%60):02d} / {int(track['duration']//60)}:{int(track['duration'])%60:02d}"
