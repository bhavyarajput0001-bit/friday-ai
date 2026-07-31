import os, json
from datetime import datetime

class ContextEngine:
    """Gathers system context to enrich LLM prompts."""
    def __init__(self):
        self._memory = None
        self._calendar = None

    def _get_memory(self):
        if self._memory is None:
            try:
                from obsidian_memory import ObsidianMemory
                self._memory = ObsidianMemory()
            except Exception as e:
                print(f"[Context] Memory init error: {e}")
                self._memory = False
        return self._memory if self._memory else None

    def _get_calendar(self):
        if self._calendar is None:
            try:
                from calendar_engine import CalendarEngine
                self._calendar = CalendarEngine()
            except Exception as e:
                print(f"[Context] Calendar init error: {e}")
                self._calendar = False
        return self._calendar if self._calendar else None

    def get_time_context(self):
        now = datetime.now()
        return {
            "date": now.strftime("%A, %B %d %Y"),
            "time": now.strftime("%I:%M %p"),
            "day": now.strftime("%A"),
        }

    def get_system_context(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            bat = psutil.sensors_battery()
            return f"CPU {cpu:.0f}%, RAM {mem.percent:.0f}%, Battery {bat.percent if bat else 'N/A'}%"
        except:
            return ""

    def get_today_context(self):
        cal = self._get_calendar()
        if not cal:
            return ""
        try:
            events = cal.get_today_summary()
            if events:
                lines = [f"  - {e['title']} at {e['start_time'][:16]}" for e in events[:5]]
                return "Today's schedule:\n" + "\n".join(lines)
        except:
            pass
        return "No events today."

    def get_memory_context(self, query, limit=3):
        mem = self._get_memory()
        if not mem:
            return ""
        try:
            results = mem.search(query, limit)
            if results:
                parts = [f"[Memory: {r['title']} - {r['content'][:200]}]" for r in results]
                return "\n".join(parts)
        except Exception as e:
            print(f"[Context] Memory search error: {e}")
        return ""

    def save_conversation(self, user, friday):
        mem = self._get_memory()
        if mem:
            try:
                mem.save_conversation(user, friday)
                return True
            except Exception as e:
                print(f"[Context] Save error: {e}")
        return False

    def build_system_prompt(self, user_query, category="GENERAL"):
        tc = self.get_time_context()
        sys_ctx = self.get_system_context()
        today = self.get_today_context()
        mem_ctx = self.get_memory_context(user_query)

        parts = [
            "You are FRIDAY — the personal AI of Bhavya. You are a fully capable JARVIS-grade companion, not a simple chatbot.",
            "PERSONA: confident, sharp, loyal, slightly witty, calm under pressure, always a step ahead. "
            "Address the user naturally. Use short, crisp sentences when they are brief; expand when the task needs depth.",
            "You have real abilities on this Mac (via tools): open apps, control music, manage tasks & agenda, "
            "read/write notes (Apple Notes, Keep, local), email (Apple Mail/Gmail), calendar (Apple/Google), "
            "search the web, run browser automation, clipboards, system scenes (focus/relax/fullscreen), git status, "
            "timers, volume/brightness, memory recall. If the user asks for any of these, do it and confirm with a short report.",
            f"Today is {tc['date']}, {tc['time']} ({tc['day']}).",
            f"System status: {sys_ctx}.",
            today,
        ]
        if mem_ctx:
            parts.append(f"Relevant memories from our past conversations:\n{mem_ctx}")
        parts.append(
            "RESPONSIBILITY: Be proactive, anticipate needs, flag conflicts in schedule, remember preferences, "
            "and never claim to have done something you haven't. If a task requires a tool, say which one you'd use. "
            "Answer naturally, be concise, and slightly witty."
        )
        return "\n".join(parts)

context = ContextEngine()
